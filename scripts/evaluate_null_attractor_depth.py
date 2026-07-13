from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from thermosafety.attention import NullAttractorConfig
from thermosafety.intervention import patch_gpt2_attention
from thermosafety.prompts import PromptCase, load_prompt_dir
from thermosafety.real_model import load_model
from thermosafety.risk_provider import RISK_SOURCES, risk_scores_for_cases

DETAIL_FIELDNAMES = [
    "layer",
    "id",
    "suite",
    "label",
    "risk",
    "risk_used",
    "m_null",
    "entropy",
    "spectral_gap",
]

SUMMARY_FIELDNAMES = [
    "layer",
    "n",
    "mean_risk",
    "jailbreak_m_null",
    "benign_m_null",
    "sep_m_null",
    "jailbreak_entropy",
    "benign_entropy",
    "sep_entropy",
    "jailbreak_spectral_gap",
    "benign_spectral_gap",
    "sep_spectral_gap",
    "jailbreak_m_null_baseline",
    "benign_m_null_baseline",
    "sep_m_null_baseline",
    "risk_attributable_sep_m_null",
    "baseline_fraction_jailbreak",
]


def select_cases(cases: list[PromptCase], suites: list[str], per_suite: int) -> list[PromptCase]:
    selected: list[PromptCase] = []
    for suite in suites:
        suite_cases = [case for case in cases if case.suite == suite]
        selected.extend(suite_cases[:per_suite])
    return selected


def mean(values: list[float]) -> float:
    return float(np.mean(values)) if values else 0.0


def write_csv(rows: list[dict[str, object]], path: str | Path, fieldnames: list[str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_sweep(
    model,
    tokenizer,
    torch,
    cases: list[PromptCase],
    layers: list[int],
    cfg: NullAttractorConfig,
    risk_by_id: dict[str, float],
    device: str,
    max_length: int,
    risk_override: float | None,
) -> list[dict[str, object]]:
    detail_rows: list[dict[str, object]] = []
    for layer in layers:
        for case in cases:
            risk = risk_by_id[case.id]
            risk_used = risk if risk_override is None else risk_override
            with patch_gpt2_attention(model, risk=risk_used, config=cfg, selected_layers={layer}) as log:
                encoded = tokenizer(case.prompt, return_tensors="pt", truncation=True, max_length=max_length).to(device)
                with torch.no_grad():
                    model(**encoded)
            detail_rows.append(
                {
                    "layer": layer,
                    "id": case.id,
                    "suite": case.suite,
                    "label": case.label,
                    "risk": risk,
                    "risk_used": risk_used,
                    "m_null": log.mean_null_mass(),
                    "entropy": log.mean("entropy"),
                    "spectral_gap": log.mean("spectral_gap"),
                }
            )
    return detail_rows


def summarize_layer(rows: list[dict[str, object]]) -> dict[str, float]:
    jailbreak = [row for row in rows if row["label"] == "jailbreak"]
    benign = [row for row in rows if row["label"] != "jailbreak"]
    jailbreak_m_null = mean([float(r["m_null"]) for r in jailbreak])
    benign_m_null = mean([float(r["m_null"]) for r in benign])
    jailbreak_entropy = mean([float(r["entropy"]) for r in jailbreak])
    benign_entropy = mean([float(r["entropy"]) for r in benign])
    jailbreak_gap = mean([float(r["spectral_gap"]) for r in jailbreak])
    benign_gap = mean([float(r["spectral_gap"]) for r in benign])
    return {
        "n": len(rows),
        "mean_risk": mean([float(r["risk"]) for r in rows]),
        "jailbreak_m_null": jailbreak_m_null,
        "benign_m_null": benign_m_null,
        "sep_m_null": jailbreak_m_null - benign_m_null,
        "jailbreak_entropy": jailbreak_entropy,
        "benign_entropy": benign_entropy,
        "sep_entropy": jailbreak_entropy - benign_entropy,
        "jailbreak_spectral_gap": jailbreak_gap,
        "benign_spectral_gap": benign_gap,
        "sep_spectral_gap": jailbreak_gap - benign_gap,
    }


def write_report(summary_rows: list[dict[str, object]], output: str | Path, model_name: str, has_baseline_control: bool) -> None:
    lines = [
        "# Null-Attractor Depth Diagnostic Report",
        "",
        f"Model: `{model_name}`. Single-layer-selected forward passes (no generation): for each tested",
        "layer, only that layer's attention is patched with the risk-gated null attractor "
        "(`thermosafety/intervention.py`), and `m_null`, entropy, and spectral gap are logged per prompt.",
        "This tests whether the original null-attractor observables show the same depth-wise growth/",
        "collapse curve found by the basin-energy diagnostic (see `results/basin_energy_diagnostic_note.md`).",
    ]
    if has_baseline_control:
        lines.extend(
            [
                "",
                "A risk-forced-to-0 control pass runs automatically alongside the real-risk pass (see",
                "`results/null_attractor_depth_diagnostic_note.md`, 'Risk=0 control'), to separate genuinely",
                "risk-conditioned separation from layer-specific baseline null mass. Use",
                "`risk_attributable_sep_m_null`, not raw `sep_m_null`, to select the strongest layer.",
            ]
        )
    lines.extend(
        [
            "",
            "## Per-Layer Summary",
            "",
        ]
    )
    if has_baseline_control:
        lines.append(
            "| layer | n | mean risk | jailbreak m_null | benign m_null | sep(m_null) | baseline sep(m_null), risk=0 | risk-attributable sep(m_null) | baseline fraction (jailbreak) | sep(entropy) | sep(spectral gap) |"
        )
        lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for row in summary_rows:
            lines.append(
                f"| {row['layer']} | {row['n']} | {float(row['mean_risk']):.3f} | "
                f"{float(row['jailbreak_m_null']):.4f} | {float(row['benign_m_null']):.4f} | {float(row['sep_m_null']):.4f} | "
                f"{float(row['sep_m_null_baseline']):.4f} | {float(row['risk_attributable_sep_m_null']):.4f} | "
                f"{float(row['baseline_fraction_jailbreak']):.2%} | {float(row['sep_entropy']):.4f} | {float(row['sep_spectral_gap']):.4f} |"
            )
    else:
        lines.append("| layer | n | mean risk | jailbreak m_null | benign m_null | sep(m_null) | sep(entropy) | sep(spectral gap) |")
        lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|")
        for row in summary_rows:
            lines.append(
                f"| {row['layer']} | {row['n']} | {float(row['mean_risk']):.3f} | "
                f"{float(row['jailbreak_m_null']):.4f} | {float(row['benign_m_null']):.4f} | {float(row['sep_m_null']):.4f} | "
                f"{float(row['sep_entropy']):.4f} | {float(row['sep_spectral_gap']):.4f} |"
            )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            "`sep(m_null)` = mean(m_null | jailbreak) - mean(m_null | benign). "
            + (
                "`risk_attributable_sep_m_null` = sep(m_null, real risk) - sep(m_null, risk=0); this is the "
                "corrected observable to use for layer selection, since raw sep(m_null) can be inflated or "
                "masked by each layer's risk-independent baseline null mass (see the note above)."
                if has_baseline_control
                else "A positive, depth-growing value here (mirroring the basin-energy depth curve) supports "
                "one unified depth-dependent phase-transition story across both diagnostics."
            ),
        ]
    )
    Path(output).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep layers for null-attractor m_null/entropy/spectral-gap depth diagnostics.")
    parser.add_argument("--prompts", default="prompts")
    parser.add_argument("--model", default="distilgpt2")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument(
        "--suites",
        default="benign,benign_complex,direct_jailbreak,obfuscated_jailbreak,long_context_jailbreak,safety_research,paraphrased_adversarial,many_shot_jailbreak",
    )
    parser.add_argument("--per-suite", type=int, default=6)
    parser.add_argument("--layers", default="4,8,12,16,18,20,21,22,23", help="Comma-separated layer indices to test.")
    parser.add_argument("--risk-source", choices=RISK_SOURCES, default="surface")
    parser.add_argument("--risk-threshold", type=float, default=0.42)
    parser.add_argument("--eta-null", type=float, default=4.0)
    parser.add_argument("--kappa", type=float, default=18.0)
    parser.add_argument("--beta-collapse", type=float, default=2.5)
    parser.add_argument("--null-key-mode", default="mean_logit", choices=["zero", "mean_logit"])
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument(
        "--force-risk",
        type=float,
        default=None,
        help="Override every prompt's risk score with this constant for a single manual pass "
        "(disables the automatic risk=0 baseline-control pass). Use the default (unset) for the "
        "normal dual-pass, baseline-corrected sweep.",
    )
    parser.add_argument(
        "--no-baseline-control",
        action="store_true",
        help="Skip the automatic risk=0 control pass and report only raw sep(m_null), roughly halving runtime.",
    )
    parser.add_argument("--baseline-risk", type=float, default=0.0, help="Risk value used for the automatic baseline-control pass.")
    parser.add_argument("--output", default="results/null_attractor_depth_detail.csv")
    parser.add_argument("--summary-output", default="results/null_attractor_depth_summary.csv")
    parser.add_argument("--report-output", default="results/null_attractor_depth_report.md")
    args = parser.parse_args()

    torch, tokenizer, model = load_model(args.model, device=args.device, local_files_only=args.local_files_only)
    suites = [suite.strip() for suite in args.suites.split(",") if suite.strip()]
    cases = select_cases(load_prompt_dir(args.prompts), suites, args.per_suite)
    risk_by_id = risk_scores_for_cases(cases, source=args.risk_source, tokenizer=tokenizer, model=model, device=args.device, max_length=args.max_length)

    layers = [int(layer.strip()) for layer in args.layers.split(",") if layer.strip()]
    cfg = NullAttractorConfig(
        risk_threshold=args.risk_threshold,
        eta_null=args.eta_null,
        kappa=args.kappa,
        beta_collapse=args.beta_collapse,
        null_key_mode=args.null_key_mode,
    )

    run_baseline_control = args.force_risk is None and not args.no_baseline_control

    detail_rows = run_sweep(model, tokenizer, torch, cases, layers, cfg, risk_by_id, args.device, args.max_length, args.force_risk)
    baseline_rows: list[dict[str, object]] = []
    if run_baseline_control:
        baseline_rows = run_sweep(model, tokenizer, torch, cases, layers, cfg, risk_by_id, args.device, args.max_length, args.baseline_risk)

    summary_rows: list[dict[str, object]] = []
    for layer in layers:
        rows = [row for row in detail_rows if row["layer"] == layer]
        summary = {"layer": layer, **summarize_layer(rows)}
        if run_baseline_control:
            baseline_layer_rows = [row for row in baseline_rows if row["layer"] == layer]
            baseline_summary = summarize_layer(baseline_layer_rows)
            summary["jailbreak_m_null_baseline"] = baseline_summary["jailbreak_m_null"]
            summary["benign_m_null_baseline"] = baseline_summary["benign_m_null"]
            summary["sep_m_null_baseline"] = baseline_summary["sep_m_null"]
            summary["risk_attributable_sep_m_null"] = summary["sep_m_null"] - baseline_summary["sep_m_null"]
            summary["baseline_fraction_jailbreak"] = (
                baseline_summary["jailbreak_m_null"] / summary["jailbreak_m_null"] if summary["jailbreak_m_null"] > 1e-9 else 0.0
            )
        else:
            summary["jailbreak_m_null_baseline"] = ""
            summary["benign_m_null_baseline"] = ""
            summary["sep_m_null_baseline"] = ""
            summary["risk_attributable_sep_m_null"] = ""
            summary["baseline_fraction_jailbreak"] = ""
        summary_rows.append(summary)

    all_detail_rows = detail_rows + [{**row, "risk_used": f"baseline_control:{row['risk_used']}"} for row in baseline_rows]
    write_csv(all_detail_rows, args.output, DETAIL_FIELDNAMES)
    write_csv(summary_rows, args.summary_output, SUMMARY_FIELDNAMES)
    write_report(summary_rows, args.report_output, args.model, run_baseline_control)
    print(f"wrote {len(all_detail_rows)} detail rows to {args.output}")
    print(f"wrote {len(summary_rows)} summary rows to {args.summary_output}")
    print(f"wrote report to {args.report_output}")


if __name__ == "__main__":
    main()
