"""Aggregate fixed-spectrum causal routing results across pretrained model families."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np


MODES = ("source_max", "source_min", "distractor_control")


def contrast_by_mode(result):
    return {
        row["mode"]: row
        for row in result.get("contrasts_vs_baseline", [])
        if isinstance(row, dict) and "mode" in row
    }


def paired_interval(values, seed, draws=10000):
    values = np.asarray(values, dtype=np.float64)
    if not len(values):
        return [float("nan"), float("nan")]
    rng = np.random.default_rng(seed)
    means = np.empty(draws, dtype=np.float64)
    for start in range(0, draws, 1000):
        count = min(1000, draws - start)
        indices = rng.integers(0, len(values), size=(count, len(values)))
        means[start:start + count] = values[indices].mean(axis=1)
    return [float(value) for value in np.quantile(means, [0.025, 0.975])]


def recover_intervals(base, condition, mode_index, length):
    base_records = base.get("records", [])
    condition_records = condition.get("records", [])
    if len(base_records) != len(condition_records) or not base_records:
        return {}
    accuracy = [
        condition_records[index]["correct"] - row["correct"]
        for index, row in enumerate(base_records)
    ]
    margin = [
        condition_records[index]["margin"] - row["margin"]
        for index, row in enumerate(base_records)
    ]
    seed = 7919 * int(length) + mode_index
    return {
        "accuracy_delta_ci95": paired_interval(accuracy, seed),
        "margin_delta_ci95": paired_interval(margin, seed + 1),
    }


def summarize_file(path):
    payload = json.loads(Path(path).read_text())
    rows = []
    for length, result in payload["lengths"].items():
        conditions = result["conditions"]
        base = conditions["baseline"]
        contrasts = contrast_by_mode(result)
        row = {
            "path": str(path),
            "model": payload["model"],
            "format": payload.get("format", "colon_newline"),
            "layer": int(payload["selected_layer"]),
            "heads": len(payload["selected_heads"]),
            "length": int(length),
            "n_examples": int(base["n_examples"]),
            "baseline_accuracy": float(base["accuracy"]),
            "baseline_margin": float(base["mean_margin"]),
            "baseline_source_mass": float(base["mean_source_mass"]),
        }
        for mode_index, mode in enumerate(MODES):
            condition = conditions[mode]
            contrast = dict(contrasts.get(mode, {}))
            recovered = recover_intervals(base, condition, mode_index, length)
            for key, value in recovered.items():
                contrast.setdefault(key, value)
            row[f"{mode}_accuracy_delta"] = float(condition["accuracy"] - base["accuracy"])
            row[f"{mode}_margin_delta"] = float(condition["mean_margin"] - base["mean_margin"])
            row[f"{mode}_source_mass_delta"] = float(
                condition["mean_source_mass"] - base["mean_source_mass"]
            )
            row[f"{mode}_max_invariant_error"] = max(
                condition["invariant_max_abs_error"].values(), default=0.0
            )
            for metric in ("accuracy_delta_ci95", "margin_delta_ci95"):
                interval = contrast.get(metric, [float("nan"), float("nan")])
                row[f"{mode}_{metric}_low"] = float(interval[0])
                row[f"{mode}_{metric}_high"] = float(interval[1])
        source_max = conditions["source_max"]
        control = conditions["distractor_control"]
        assignment_intervals = recover_intervals(control, source_max, len(MODES), length)
        row["source_max_vs_control_accuracy_delta"] = float(
            source_max["accuracy"] - control["accuracy"]
        )
        row["source_max_vs_control_margin_delta"] = float(
            source_max["mean_margin"] - control["mean_margin"]
        )
        for metric, interval in assignment_intervals.items():
            row[f"source_max_vs_control_{metric}_low"] = float(interval[0])
            row[f"source_max_vs_control_{metric}_high"] = float(interval[1])
        rows.append(row)
    return rows


def write_csv(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_report(path, rows):
    lines = [
        "# Pretrained Causal Routing Summary",
        "",
        "Each intervention acts in one calibration-selected layer and preserves the complete selected-head",
        "attention spectrum. Deltas are paired against the natural model on identical examples.",
        "",
        "| model | N | baseline acc | max dacc [95% CI] | max-ctrl dacc [95% CI] | min dacc [95% CI] | ctrl dacc | max dmargin [95% CI] | max-ctrl dmargin [95% CI] | min dmargin [95% CI] | ctrl dmargin | invariant err |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        invariant = max(row[f"{mode}_max_invariant_error"] for mode in MODES)
        acc_ci = (row["source_max_accuracy_delta_ci95_low"], row["source_max_accuracy_delta_ci95_high"])
        margin_ci = (row["source_max_margin_delta_ci95_low"], row["source_max_margin_delta_ci95_high"])
        assignment_acc_ci = (
            row["source_max_vs_control_accuracy_delta_ci95_low"],
            row["source_max_vs_control_accuracy_delta_ci95_high"],
        )
        assignment_margin_ci = (
            row["source_max_vs_control_margin_delta_ci95_low"],
            row["source_max_vs_control_margin_delta_ci95_high"],
        )
        min_acc_ci = (
            row["source_min_accuracy_delta_ci95_low"],
            row["source_min_accuracy_delta_ci95_high"],
        )
        min_margin_ci = (
            row["source_min_margin_delta_ci95_low"],
            row["source_min_margin_delta_ci95_high"],
        )
        acc_text = f"{row['source_max_accuracy_delta']:+.3f}"
        margin_text = f"{row['source_max_margin_delta']:+.3f}"
        assignment_acc_text = f"{row['source_max_vs_control_accuracy_delta']:+.3f}"
        assignment_margin_text = f"{row['source_max_vs_control_margin_delta']:+.3f}"
        min_acc_text = f"{row['source_min_accuracy_delta']:+.3f}"
        min_margin_text = f"{row['source_min_margin_delta']:+.3f}"
        if all(value == value for value in acc_ci):
            acc_text += f" [{acc_ci[0]:+.3f},{acc_ci[1]:+.3f}]"
        if all(value == value for value in margin_ci):
            margin_text += f" [{margin_ci[0]:+.3f},{margin_ci[1]:+.3f}]"
        if all(value == value for value in assignment_acc_ci):
            assignment_acc_text += (
                f" [{assignment_acc_ci[0]:+.3f},{assignment_acc_ci[1]:+.3f}]"
            )
        if all(value == value for value in assignment_margin_ci):
            assignment_margin_text += (
                f" [{assignment_margin_ci[0]:+.3f},{assignment_margin_ci[1]:+.3f}]"
            )
        if all(value == value for value in min_acc_ci):
            min_acc_text += f" [{min_acc_ci[0]:+.3f},{min_acc_ci[1]:+.3f}]"
        if all(value == value for value in min_margin_ci):
            min_margin_text += f" [{min_margin_ci[0]:+.3f},{min_margin_ci[1]:+.3f}]"
        model_label = row["model"]
        if row["format"] != "colon_newline":
            model_label += f" [{row['format']}]"
        lines.append(
            f"| {model_label} | {row['length']} | {row['baseline_accuracy']:.3f} | "
            f"{acc_text} | {assignment_acc_text} | {min_acc_text} | "
            f"{row['distractor_control_accuracy_delta']:+.3f} | "
            f"{margin_text} | {assignment_margin_text} | {min_margin_text} | "
            f"{row['distractor_control_margin_delta']:+.3f} | {invariant:.3g} |"
        )
    Path(path).write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+")
    parser.add_argument("--csv-out", default="results/lengthgen/pretrained_causal_routing_summary.csv")
    parser.add_argument("--report-out", default="results/lengthgen/pretrained_causal_routing_summary.md")
    args = parser.parse_args()
    rows = []
    for path in args.inputs:
        rows.extend(summarize_file(path))
    if not rows:
        raise SystemExit("no pretrained causal rows")
    rows.sort(key=lambda row: (row["model"], row["format"], row["length"]))
    write_csv(args.csv_out, rows)
    write_report(args.report_out, rows)
    print(Path(args.report_out).as_posix())


if __name__ == "__main__":
    main()
