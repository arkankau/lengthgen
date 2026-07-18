"""Aggregate saved Qwen activation-patching baseline summaries."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
PRIMARY_PATTERN = (
    "results/lengthgen/activation_patching_qwen1p5b_s*/"
    "pretrained_activation_patching_baseline.json"
)
RELEASE_PATTERN = (
    "results/activation_patching_qwen1p5b_s*/"
    "pretrained_activation_patching_baseline.json"
)
IS_RELEASE = not list(REPO_ROOT.glob(PRIMARY_PATTERN)) and bool(
    list(REPO_ROOT.glob(RELEASE_PATTERN))
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pattern",
        default=RELEASE_PATTERN if IS_RELEASE else PRIMARY_PATTERN,
    )
    parser.add_argument(
        "--out-json",
        default=(
            "results/activation_patching_qwen1p5b_summary.json"
            if IS_RELEASE
            else "results/lengthgen/activation_patching_qwen1p5b_summary.json"
        ),
    )
    parser.add_argument(
        "--out-report",
        default=(
            "results/activation_patching_qwen1p5b_summary.md"
            if IS_RELEASE
            else "results/lengthgen/activation_patching_qwen1p5b_summary.md"
        ),
    )
    args = parser.parse_args()

    paths = sorted(REPO_ROOT.glob(args.pattern))
    if not paths:
        raise FileNotFoundError(f"no result files match {args.pattern}")
    rows = [json.loads(path.read_text()) for path in paths]

    fields = {
        "fixed_spectrum_swap_margin_delta": "Fixed-spectrum swap",
        "source_value_corruption_margin_delta": "Source-value corruption",
        "clean_to_corrupt_activation_patch_rescue": "Activation-patch rescue",
        "median_fraction_of_corruption_damage_recovered": "Median damage recovered",
        "fixed_spectrum_mean_l1_displacement": "Swap L1 displacement",
        "activation_patch_rms_displacement": "Activation RMS displacement",
        "fixed_spectrum_max_abs_invariant_error": "Invariant error",
    }
    aggregates = {}
    for field, label in fields.items():
        values = np.asarray([row["summary"][field] for row in rows], dtype=np.float64)
        aggregates[field] = {
            "label": label,
            "mean": float(values.mean()),
            "seed_range": [float(values.min()), float(values.max())],
            "seed_values": values.tolist(),
        }

    result = {
        "model": rows[0]["model"],
        "n_seeds": len(rows),
        "examples_per_seed": [row["summary"]["n_examples"] for row in rows],
        "selected_layers": [row["selected_layer"] for row in rows],
        "selected_heads": [row["selected_heads"] for row in rows],
        "aggregates": aggregates,
        "source_files": [str(path.relative_to(REPO_ROOT)) for path in paths],
    }

    out_json = REPO_ROOT / args.out_json
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2) + "\n")

    lines = [
        "# Qwen Activation-Patching Baseline",
        "",
        f"Model: {result['model']}; seeds: {result['n_seeds']}; "
        f"examples per seed: {result['examples_per_seed']}.",
        "",
        "| Quantity | Mean | Seed range |",
        "|---|---:|---:|",
    ]
    for field in fields:
        row = aggregates[field]
        low, high = row["seed_range"]
        lines.append(f"| {row['label']} | {row['mean']:+.6f} | [{low:+.6f}, {high:+.6f}] |")
    lines += [
        "",
        "The two interventions have different estimands. The fixed-spectrum swap measures assignment "
        "sensitivity on an unchanged prompt. Activation patching measures restoration after replacing "
        "the source value and importing clean selected-head outputs.",
    ]
    out_report = REPO_ROOT / args.out_report
    out_report.write_text("\n".join(lines) + "\n")
    print(f"Wrote {out_json} and {out_report}")


if __name__ == "__main__":
    main()
