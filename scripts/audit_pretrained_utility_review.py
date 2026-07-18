"""Produce reviewer-facing diagnostics from pretrained utility audit artifacts.

The source-max circuits in these artifacts are chosen on a disjoint calibration
split.  This script intentionally evaluates only the saved evaluation records:
it reports calibration error and how often a selected circuit has no movable
source mass because every selected head already places the source at its row
maximum.
"""
from __future__ import annotations

import argparse
import glob
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


def percentile(values, q):
    return float(np.quantile(np.asarray(values, dtype=np.float64), q))


def regression(predicted, observed):
    predicted = np.asarray(predicted, dtype=np.float64)
    observed = np.asarray(observed, dtype=np.float64)
    slope, intercept = np.polyfit(predicted, observed, 1)
    fitted = slope * predicted + intercept
    residual = observed - predicted
    return {
        "n": int(len(predicted)),
        "pearson": float(np.corrcoef(predicted, observed)[0, 1]),
        "slope": float(slope),
        "intercept": float(intercept),
        "mae": float(np.abs(residual).mean()),
        "rmse": float(np.sqrt(np.square(residual).mean())),
        "mean_signed_error": float(residual.mean()),
        "p90_absolute_error": percentile(np.abs(residual), 0.90),
        "underprediction_fraction": float(np.mean(residual > 0)),
    }


def summarize_cell(records):
    predicted = [row["first_order_margin_delta"] for row in records]
    observed = [row["exact_margin_delta"] for row in records]
    total_transfer = [sum(row["transfer_by_head"]) for row in records]
    active = np.asarray(total_transfer) > 1e-8
    return {
        "calibration": regression(predicted, observed),
        "source_already_max_all_selected_fraction": float(np.mean(~active)),
        "active_source_reassignment_fraction": float(np.mean(active)),
        "median_total_transferred_mass": percentile(total_transfer, 0.50),
        "p90_total_transferred_mass": percentile(total_transfer, 0.90),
    }


def label(model):
    lowered = model.lower()
    if "qwen" in lowered:
        return "Qwen2.5-1.5B"
    if "pythia" in lowered:
        return "Pythia-1.4B"
    if "gemma" in lowered:
        return "Gemma-2-2B"
    return model


def audit(paths):
    cells = []
    raw_cells = defaultdict(list)
    for raw_path in paths:
        with open(raw_path) as handle:
            artifact = json.load(handle)
        for length, payload in artifact["lengths"].items():
            records = payload["source_max"]["records"]
            model = label(artifact["model"])
            raw_cells[model].extend(records)
            cells.append({
                "model": model,
                "seed": int(artifact["seed"]),
                "length": int(length),
                **summarize_cell(records),
            })

    by_model = defaultdict(list)
    for cell in cells:
        by_model[cell["model"]].append(cell)

    families = {}
    for model in sorted(by_model):
        records = raw_cells[model]
        prediction = [row["first_order_margin_delta"] for row in records]
        observed = [row["exact_margin_delta"] for row in records]
        transfer = [sum(row["transfer_by_head"]) for row in records]
        zero = [abs(value) <= 1e-8 for value in transfer]
        families[model] = {
            "n_evaluation_examples": len(prediction),
            "calibration": regression(prediction, observed),
            "source_already_max_all_selected_fraction": float(np.mean(zero)),
            "median_total_transferred_mass": percentile(transfer, 0.50),
            "p90_total_transferred_mass": percentile(transfer, 0.90),
        }
    return {"cells": cells, "families": families}


def report(result):
    lines = [
        "# Pretrained Utility Reviewer Audit",
        "",
        "All figures below use saved evaluation records. The underlying circuits were selected on separate calibration examples.",
        "",
        "| Model | Eval. examples | Pearson | Slope | Intercept | MAE | Source already max in all selected heads | Median transferred mass | P90 transferred mass |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model, row in result["families"].items():
        fit = row["calibration"]
        lines.append(
            f"| {model} | {row['n_evaluation_examples']} | {fit['pearson']:.3f} | "
            f"{fit['slope']:.3f} | {fit['intercept']:+.3f} | {fit['mae']:.3f} | "
            f"{row['source_already_max_all_selected_fraction']:.1%} | "
            f"{row['median_total_transferred_mass']:.3f} | {row['p90_total_transferred_mass']:.3f} |"
        )
    lines += [
        "",
        "The slope and error statistics are calibration diagnostics, not additional evidence of causal effect. "
        "A source-already-max row produces a zero source-max intervention for the selected circuit and is retained rather than discarded.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pattern",
        default="results/lengthgen/pretrained_utility*/pretrained_utility_gap_results.json",
    )
    parser.add_argument(
        "--out-json",
        default="results/lengthgen/pretrained_utility_reviewer_audit.json",
    )
    parser.add_argument(
        "--out-report",
        default="results/lengthgen/pretrained_utility_reviewer_audit.md",
    )
    args = parser.parse_args()
    paths = sorted(glob.glob(args.pattern))
    if not paths:
        raise FileNotFoundError(f"No files matched {args.pattern!r}")
    result = audit(paths)
    Path(args.out_json).write_text(json.dumps(result, indent=2) + "\n")
    Path(args.out_report).write_text(report(result))
    print(f"Audited {len(paths)} artifacts and wrote {args.out_report}")


if __name__ == "__main__":
    main()
