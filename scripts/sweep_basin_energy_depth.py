from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from thermosafety.basin_energy import (
    basin_energies,
    basin_selectivity,
    competition_margin,
    orient_basis,
    residual_subspace_coupling,
    signed_axis_projection,
)
from thermosafety.prompts import PromptCase, load_prompt_dir
from thermosafety.real_model import extract_trace_from_loaded, load_model

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_basin_energy import (  # noqa: E402
    DEFAULT_BENIGN_ANCHOR,
    DEFAULT_SAFE_ANCHOR,
    DEFAULT_UNSAFE_ANCHOR,
    REFUSAL_UNSAFE_PAIRS,
    calibrate_refusal_subspace,
    calibrate_single_anchors,
    pooled_hidden_state,
)

SUMMARY_FIELDNAMES = [
    "model",
    "layer",
    "n",
    "sep_margin_single_anchor",
    "sep_margin_subspace_primary_axis",
    "sep_residual_subspace_coupling",
    "correlation_single_vs_subspace",
]


def select_cases(cases: list[PromptCase], suites: list[str], per_suite: int) -> list[PromptCase]:
    selected: list[PromptCase] = []
    for suite in suites:
        suite_cases = [case for case in cases if case.suite == suite]
        selected.extend(suite_cases[:per_suite])
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep layers for the basin-energy diagnostic, saving a combined depth-curve CSV.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-label", default=None, help="Short label to record in the 'model' column (defaults to --model).")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument(
        "--suites",
        default="benign,benign_complex,direct_jailbreak,obfuscated_jailbreak,long_context_jailbreak,safety_research,paraphrased_adversarial,many_shot_jailbreak",
    )
    parser.add_argument("--per-suite", type=int, default=6)
    parser.add_argument("--layers", required=True, help="Comma-separated layer indices to test.")
    parser.add_argument("--subspace-k", type=int, default=2)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--safe-anchor", default=DEFAULT_SAFE_ANCHOR)
    parser.add_argument("--unsafe-anchor", default=DEFAULT_UNSAFE_ANCHOR)
    parser.add_argument("--benign-anchor", default=DEFAULT_BENIGN_ANCHOR)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    model_label = args.model_label or args.model
    torch, tokenizer, model = load_model(args.model, device=args.device, local_files_only=args.local_files_only)
    suites = [suite.strip() for suite in args.suites.split(",") if suite.strip()]
    cases = select_cases(load_prompt_dir("prompts"), suites, args.per_suite)
    layers = [int(layer.strip()) for layer in args.layers.split(",") if layer.strip()]

    rows: list[dict[str, object]] = []
    for layer in layers:
        centroids = calibrate_single_anchors(
            tokenizer, model, torch, args.device, layer, args.max_length,
            args.safe_anchor, args.unsafe_anchor, args.benign_anchor,
        )
        subspace, reference = calibrate_refusal_subspace(
            tokenizer, model, torch, args.device, layer, args.max_length, REFUSAL_UNSAFE_PAIRS, args.subspace_k,
        )
        subspace = orient_basis(subspace, reference)

        labels: list[bool] = []
        single_margins: list[float] = []
        subspace_margins: list[float] = []
        residual_couplings: list[float] = []
        for case in cases:
            trace = extract_trace_from_loaded(
                prompt=case.prompt, torch=torch, tokenizer=tokenizer, model=model, max_length=args.max_length, device=args.device
            )
            h = pooled_hidden_state(trace.hidden_states, layer)
            energies = basin_energies(h, centroids)
            single_margins.append(competition_margin(energies, safe_key="safe", unsafe_key="unsafe"))
            subspace_margins.append(signed_axis_projection(h, subspace[0]))
            residual_couplings.append(residual_subspace_coupling(h, subspace))
            labels.append(case.label == "jailbreak")

        correlation = float(np.corrcoef(single_margins, subspace_margins)[0, 1]) if len(cases) > 1 else 0.0
        rows.append(
            {
                "model": model_label,
                "layer": layer,
                "n": len(cases),
                "sep_margin_single_anchor": basin_selectivity(single_margins, labels),
                "sep_margin_subspace_primary_axis": basin_selectivity(subspace_margins, labels),
                "sep_residual_subspace_coupling": basin_selectivity(residual_couplings, labels),
                "correlation_single_vs_subspace": correlation,
            }
        )
        print(f"layer {layer}: {rows[-1]}")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {output}")


if __name__ == "__main__":
    main()
