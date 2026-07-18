"""Aggregate frozen-circuit natural-QA length ladders."""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np

from analyze_pretrained_utility_selection import hierarchical_interval


def _records(result, length, condition):
    return result["lengths"][str(length)]["conditions"][condition]["records"]


def _field(result, length, condition, field):
    return np.asarray([row[field] for row in _records(result, length, condition)], dtype=float)


def _rescue(result, length, field):
    return _field(result, length, "source_max", field) - _field(
        result, length, "matched_distractor_control", field
    )


def _condition_delta(result, length, left, right, field):
    return _field(result, length, left, field) - _field(result, length, right, field)


def _invariant_error(diagnostics):
    if not diagnostics:
        return 0.0
    invariant_keys = {
        "sorted_weights",
        "entropy",
        "l1_norm",
        "l2_norm",
        "linf_norm",
        "participation_ratio",
    }
    values = [abs(float(value)) for key, value in diagnostics.items() if key in invariant_keys]
    return max(values, default=0.0)


def _summary(groups, seed):
    values = np.concatenate(groups)
    return {
        "n_seeds": len(groups),
        "n_examples": int(values.size),
        "mean": float(values.mean()),
        "ci95": hierarchical_interval(groups, seed),
        "seed_means": [float(group.mean()) for group in groups],
    }


def aggregate(results, expected_seeds=(0, 1, 2)):
    ordered = sorted(results, key=lambda row: int(row["seed"]))
    models = {row.get("model") for row in ordered}
    if len(models) > 1:
        raise ValueError(f"natural-QA ladder results must be analyzed per model, got {sorted(models)}")
    passing = [row for row in ordered if row.get("pilot", {}).get("gate_pass") and row.get("lengths")]
    if not passing:
        return {
            "model": next(iter(models), None),
            "available_seeds": [int(row["seed"]) for row in ordered],
            "passing_seeds": [],
            "preregistered_success": False,
        }
    lengths = passing[0]["passage_counts"]
    shortest, longest = min(lengths), max(lengths)
    trajectory = {}
    for length in lengths:
        trajectory[str(length)] = {
            "baseline_source_mass": _summary(
                [_field(row, length, "baseline", "source_mass") for row in passing], 800_000 + length
            ),
            "baseline_margin": _summary(
                [_field(row, length, "baseline", "margin") for row in passing], 810_000 + length
            ),
            "baseline_accuracy": _summary(
                [_field(row, length, "baseline", "correct") for row in passing], 820_000 + length
            ),
            "rescue_margin": _summary(
                [_rescue(row, length, "margin") for row in passing], 830_000 + length
            ),
            "rescue_accuracy": _summary(
                [_rescue(row, length, "correct") for row in passing], 840_000 + length
            ),
            "control_minus_baseline_margin": _summary(
                [
                    _condition_delta(
                        row, length, "matched_distractor_control", "baseline", "margin"
                    )
                    for row in passing
                ],
                845_000 + length,
            ),
        }
    long_minus_short = {
        "baseline_source_mass": _summary([
            _field(row, longest, "baseline", "source_mass")
            - _field(row, shortest, "baseline", "source_mass") for row in passing
        ], 850_000),
        "baseline_margin": _summary([
            _field(row, longest, "baseline", "margin")
            - _field(row, shortest, "baseline", "margin") for row in passing
        ], 860_000),
        "baseline_accuracy": _summary([
            _field(row, longest, "baseline", "correct")
            - _field(row, shortest, "baseline", "correct") for row in passing
        ], 870_000),
        "rescue_amplification_margin": _summary([
            _rescue(row, longest, "margin") - _rescue(row, shortest, "margin")
            for row in passing
        ], 880_000),
    }
    invariant_error = max(
        _invariant_error(condition.get("invariant_max_abs_error", {}))
        for row in passing
        for length_row in row["lengths"].values()
        for condition in length_row["conditions"].values()
    )
    full_size = [
        int(row["seed"]) for row in passing
        if len(row.get("example_ids", {}).get("calibration", [])) >= 64
        and len(row.get("example_ids", {}).get("evaluation", [])) >= 128
    ]
    success = bool(
        len(full_size) >= 2
        and long_minus_short["baseline_source_mass"]["ci95"][1] < 0
        and long_minus_short["baseline_margin"]["ci95"][1] < 0
        and trajectory[str(longest)]["rescue_margin"]["ci95"][0] > 0
        and invariant_error <= 1e-5
    )
    return {
        "model": next(iter(models), None),
        "expected_seeds": list(expected_seeds),
        "available_seeds": [int(row["seed"]) for row in ordered],
        "passing_seeds": [int(row["seed"]) for row in passing],
        "passage_counts": lengths,
        "frozen_at_passage_count": shortest,
        "trajectory": trajectory,
        "longest_minus_shortest": long_minus_short,
        "invariant_max_abs_error": invariant_error,
        "full_size_seeds": full_size,
        "preregistered_success": success,
    }


def markdown(summary):
    lines = ["# Natural-QA Length Ladder", ""]
    if not summary.get("passing_seeds"):
        return "\n".join(lines + ["No competent completed seed is available.", ""])
    lines += [
        f"Preregistered result: **{'pass' if summary['preregistered_success'] else 'fail/pending'}**.",
        f"The utility-selected circuit was frozen at {summary['frozen_at_passage_count']} passages.",
        "",
        "| Passages | Baseline source mass | Baseline margin | Baseline accuracy | Max-control margin | Control-baseline margin |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for length in summary["passage_counts"]:
        row = summary["trajectory"][str(length)]
        lines.append(
            f"| {length} | {row['baseline_source_mass']['mean']:.3f} | "
            f"{row['baseline_margin']['mean']:+.3f} | {row['baseline_accuracy']['mean']:.3f} | "
            f"{row['rescue_margin']['mean']:+.3f} | "
            f"{row['control_minus_baseline_margin']['mean']:+.3f} |"
        )
    lines += ["", "| Longest minus shortest | Mean | 95% CI |", "|---|---:|---:|"]
    for name, row in summary["longest_minus_shortest"].items():
        lines.append(f"| {name.replace('_', ' ')} | {row['mean']:+.3f} | [{row['ci95'][0]:+.3f}, {row['ci95'][1]:+.3f}] |")
    lines += [
        "",
        f"Maximum spectrum-invariant error: `{summary['invariant_max_abs_error']:.3g}`.",
        "Hierarchical intervals resample seeds and paired questions.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="*", default=[
        "results/lengthgen/pretrained_natural_mcqa_ladder/*/pretrained_natural_mcqa_ladder_results.json"
    ])
    parser.add_argument("--json-output", default="results/lengthgen/pretrained_natural_mcqa_ladder_summary.json")
    parser.add_argument("--md-output", default="results/lengthgen/pretrained_natural_mcqa_ladder_summary.md")
    args = parser.parse_args()
    paths = []
    for pattern in args.inputs:
        paths.extend(glob.glob(pattern) or [pattern])
    results = [json.loads(Path(path).read_text()) for path in sorted(set(paths)) if Path(path).exists()]
    summary = aggregate(results)
    Path(args.json_output).write_text(json.dumps(summary, indent=2) + "\n")
    Path(args.md_output).write_text(markdown(summary))
    print(f"wrote {args.json_output}")
    print(f"wrote {args.md_output}")


if __name__ == "__main__":
    main()
