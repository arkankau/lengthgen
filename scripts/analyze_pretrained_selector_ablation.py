"""Aggregate the preregistered equal-budget selector ablation."""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np

from analyze_pretrained_utility_selection import hierarchical_interval


COMPARATORS = (
    "source_mass",
    "transfer_mass",
    "utility_gap",
    "source_gradient",
    "gradient_magnitude",
)


def effect(result, selector):
    row = result["selectors"][selector]
    source = row["source_max"]["records"]
    control = row["distractor_control"]["records"]
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


def aggregate(results, expected_seeds=tuple(range(10))):
    ordered = sorted(results, key=lambda row: int(row["seed"]))
    available = [int(row["seed"]) for row in ordered]
    selector_names = list(ordered[0]["selectors"]) if ordered else []
    groups = {
        name: [effect(result, name) for result in ordered]
        for name in selector_names
    }
    selectors = {
        name: summarize_groups(current, 100_000 + index)
        for index, (name, current) in enumerate(groups.items())
    }
    utility = groups.get("utility_gain", [])
    pairwise = {}
    for index, name in enumerate(COMPARATORS):
        differences = [
            utility[seed_index] - groups[name][seed_index]
            for seed_index in range(len(ordered))
        ]
        pairwise[name] = summarize_groups(differences, 200_000 + index)

    ranking = sorted(
        selector_names, key=lambda name: selectors[name]["mean"], reverse=True
    )
    positive_primary = bool(
        utility and selectors["utility_gain"]["ci95"][0] > 0
    )
    mean_advantages = bool(
        pairwise and all(row["mean"] > 0 for row in pairwise.values())
    )
    universal_superiority = bool(
        pairwise and all(row["ci95"][0] > 0 for row in pairwise.values())
    )
    return {
        "expected_seeds": list(expected_seeds),
        "available_seeds": available,
        "missing_seeds": sorted(set(expected_seeds) - set(available)),
        "selectors": selectors,
        "ranking": ranking,
        "utility_gain_pairwise_advantage": pairwise,
        "primary_interval_positive": positive_primary,
        "utility_gain_ranks_first": bool(ranking and ranking[0] == "utility_gain"),
        "all_preregistered_mean_advantages_positive": mean_advantages,
        "preregistered_success": bool(
            positive_primary and ranking and ranking[0] == "utility_gain" and mean_advantages
        ),
        "universal_superiority_supported": universal_superiority,
    }


def markdown_report(summary):
    lines = [
        "# Pretrained Selector Ablation Summary",
        "",
        f"Preregistered success rule: **{'pass' if summary['preregistered_success'] else 'fail'}**.",
        f"Universal superiority: **{'supported' if summary['universal_superiority_supported'] else 'not supported'}**.",
        f"Seeds: `{summary['available_seeds']}`; missing: `{summary['missing_seeds']}`.",
        "",
        "| Selector | Mean max-control margin | Hierarchical 95% CI | Seed means |",
        "|---|---:|---:|:---|",
    ]
    for name in summary["ranking"]:
        row = summary["selectors"][name]
        seed_means = ", ".join(f"{value:+.3f}" for value in row["seed_means"])
        lines.append(
            f"| {name} | {row['mean']:+.3f} | "
            f"[{row['ci95'][0]:+.3f}, {row['ci95'][1]:+.3f}] | {seed_means} |"
        )
    lines += [
        "",
        "## Utility-Gain Specificity",
        "",
        "| Comparator | Utility minus comparator | Hierarchical 95% CI |",
        "|---|---:|---:|",
    ]
    for name, row in summary["utility_gain_pairwise_advantage"].items():
        lines.append(
            f"| {name} | {row['mean']:+.3f} | "
            f"[{row['ci95'][0]:+.3f}, {row['ci95'][1]:+.3f}] |"
        )
    lines += [
        "",
        "A positive utility-gain effect establishes usefulness. Ranking first and beating the "
        "five preregistered alternatives addresses selector specificity. A universal "
        "superiority claim is withheld unless every paired hierarchical interval excludes zero.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inputs", nargs="*",
        default=[
            "results/lengthgen/pretrained_selector_ablation_smollm2_s*/"
            "pretrained_selector_ablation_results.json"
        ],
    )
    parser.add_argument(
        "--json-output",
        default="results/lengthgen/pretrained_selector_ablation_summary.json",
    )
    parser.add_argument(
        "--md-output",
        default="results/lengthgen/pretrained_selector_ablation_summary.md",
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
