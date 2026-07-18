"""Aggregate gated context-grounded natural-QA routing runs."""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np

from analyze_pretrained_utility_selection import hierarchical_interval


def selector_effect(result, selector):
    conditions = result["selectors"][selector]["conditions"]
    source = conditions["source_max"]["records"]
    control = conditions["matched_distractor_control"]["records"]
    return np.asarray([
        source[index]["margin"] - record["margin"]
        for index, record in enumerate(control)
    ], dtype=np.float64)


def summarize_groups(groups, seed):
    values = np.concatenate(groups)
    return {
        "n_calibration_seeds": len(groups),
        "n_examples": int(len(values)),
        "mean": float(values.mean()),
        "ci95": hierarchical_interval(groups, seed),
        "seed_means": [float(group.mean()) for group in groups],
        "positive_fraction": float(np.mean(values > 0)),
    }


def aggregate(results, expected_seeds=(0, 1, 2)):
    ordered = sorted(results, key=lambda row: int(row["seed"]))
    available = [int(row["seed"]) for row in ordered]
    passing = [row for row in ordered if row["pilot"]["gate_pass"]]
    pilot_rows = {
        str(row["seed"]): {
            "main_accuracy": row["pilot"]["main"]["accuracy"],
            "gold_only_accuracy": row["pilot"]["gold_only"]["accuracy"],
            "no_context_accuracy": row["pilot"]["no_context"]["accuracy"],
            "context_accuracy_gain": row["pilot"]["context_accuracy_gain"],
            "gate_pass": row["pilot"]["gate_pass"],
        }
        for row in ordered
    }
    selectors = {}
    difference = None
    if passing:
        for index, selector in enumerate(("source_mass", "utility_gain")):
            groups = [selector_effect(row, selector) for row in passing]
            selectors[selector] = summarize_groups(groups, 400_000 + index)
        utility_groups = [selector_effect(row, "utility_gain") for row in passing]
        mass_groups = [selector_effect(row, "source_mass") for row in passing]
        difference = summarize_groups(
            [utility - mass for utility, mass in zip(utility_groups, mass_groups)],
            410_000,
        )
    enough_gates = len(passing) >= 2
    primary_positive = bool(
        enough_gates and selectors["utility_gain"]["ci95"][0] > 0
    )
    utility_beats_mass = bool(
        enough_gates and difference is not None and difference["mean"] > 0
    )
    success = bool(enough_gates and primary_positive and utility_beats_mass)
    return {
        "expected_seeds": list(expected_seeds),
        "available_seeds": available,
        "missing_seeds": sorted(set(expected_seeds) - set(available)),
        "pilot": pilot_rows,
        "passing_seeds": [int(row["seed"]) for row in passing],
        "at_least_two_gates_pass": enough_gates,
        "selectors": selectors,
        "utility_minus_source_mass": difference,
        "primary_interval_positive": primary_positive,
        "utility_mean_exceeds_source_mass": utility_beats_mass,
        "preregistered_success": success,
        "multi_evidence_triggered": success,
    }


def markdown_report(summary):
    lines = [
        "# Pretrained Natural-QA Summary",
        "",
        f"Preregistered success rule: **{'pass' if summary['preregistered_success'] else 'fail'}**.",
        f"Multi-evidence trigger: **{'yes' if summary['multi_evidence_triggered'] else 'no'}**.",
        f"Seeds passing the untouched competence gate: `{summary['passing_seeds']}`.",
        "",
        "| Seed | Main acc. | Gold-only acc. | No-context acc. | Context gain | Gate |",
        "|---:|---:|---:|---:|---:|:---:|",
    ]
    for seed, row in summary["pilot"].items():
        lines.append(
            f"| {seed} | {row['main_accuracy']:.3f} | {row['gold_only_accuracy']:.3f} | "
            f"{row['no_context_accuracy']:.3f} | {row['context_accuracy_gain']:+.3f} | "
            f"{'pass' if row['gate_pass'] else 'fail'} |"
        )
    if summary["selectors"]:
        lines += [
            "",
            "| Selector | Source max minus matched control | Resampled 95% CI |",
            "|---|---:|---:|",
        ]
        for name, row in summary["selectors"].items():
            lines.append(
                f"| {name} | {row['mean']:+.3f} | "
                f"[{row['ci95'][0]:+.3f}, {row['ci95'][1]:+.3f}] |"
            )
        difference = summary["utility_minus_source_mass"]
        lines.append(
            f"| utility minus source-mass | {difference['mean']:+.3f} | "
            f"[{difference['ci95'][0]:+.3f}, {difference['ci95'][1]:+.3f}] |"
        )
    lines += [
        "",
        "Selector effects are diagnostic over gate-passing seeds only. When one seed passes, "
        "the intervals resample paired examples within that seed and do not establish "
        "cross-seed generality.",
        "",
        "The competence gate is evaluated before calibration or intervention. Multi-evidence "
        "QA is attempted only if at least two untouched single-evidence runs pass and the "
        "held-out causal result satisfies the full preregistered rule.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inputs", nargs="*",
        default=[
            "results/lengthgen/pretrained_natural_qa_qwen_s*/"
            "pretrained_natural_qa_results.json"
        ],
    )
    parser.add_argument(
        "--json-output",
        default="results/lengthgen/pretrained_natural_qa_summary.json",
    )
    parser.add_argument(
        "--md-output",
        default="results/lengthgen/pretrained_natural_qa_summary.md",
    )
    args = parser.parse_args()
    paths = []
    for pattern in args.inputs:
        paths.extend(glob.glob(pattern) or [pattern])
    results = [json.loads(Path(path).read_text()) for path in sorted(set(paths))]
    summary = aggregate(results)
    Path(args.json_output).write_text(json.dumps(summary, indent=2) + "\n")
    Path(args.md_output).write_text(markdown_report(summary))
    print(f"wrote {args.json_output}")
    print(f"wrote {args.md_output}")


if __name__ == "__main__":
    main()
