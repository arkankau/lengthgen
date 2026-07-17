"""Compare equal-budget head selectors across pretrained model families."""
from __future__ import annotations

import argparse
import glob
import json
from collections import defaultdict
from pathlib import Path

from analyze_pretrained_selector_ablation import aggregate


def family_aggregate(results, expected_seeds=(0, 1, 2)):
    grouped = defaultdict(list)
    for result in results:
        grouped[result["model"]].append(result)
    models = {
        model: aggregate(rows, expected_seeds=expected_seeds)
        for model, rows in sorted(grouped.items())
    }
    complete = [row for row in models.values() if not row["missing_seeds"]]
    ranking_counts = defaultdict(int)
    for row in complete:
        if row["ranking"]:
            ranking_counts[row["ranking"][0]] += 1
    return {
        "expected_seeds_per_model": list(expected_seeds),
        "models": models,
        "complete_models": len(complete),
        "top_selector_counts": dict(ranking_counts),
        "cross_family_claim": (
            "supported" if len(complete) >= 3 and len(ranking_counts) == 1
            else "heterogeneous_or_incomplete"
        ),
    }


def markdown(summary):
    lines = [
        "# Pretrained Selector Family Summary",
        "",
        f"Cross-family selector result: **{summary['cross_family_claim']}**.",
        "",
        "| Model | Seeds | Top selector | Top effect | Utility rank |",
        "|---|:---|---|---:|---:|",
    ]
    for model, row in summary["models"].items():
        top = row["ranking"][0] if row["ranking"] else "n/a"
        top_effect = row["selectors"][top]["mean"] if row["ranking"] else float("nan")
        utility_rank = row["ranking"].index("utility_gain") + 1 if "utility_gain" in row["ranking"] else -1
        lines.append(
            f"| {model} | {row['available_seeds']} | {top} | {top_effect:+.3f} | {utility_rank} |"
        )
    lines += [
        "",
        "Each model uses the same calibration budget, held-out evaluation size, and selector set.",
        "A universal selector is claimed only when at least three complete families agree.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inputs", nargs="*",
        default=[
            "results/lengthgen/pretrained_selector_family_*/"
            "pretrained_selector_ablation_results.json"
        ],
    )
    parser.add_argument(
        "--json-output", default="results/lengthgen/pretrained_selector_family_summary.json"
    )
    parser.add_argument(
        "--md-output", default="results/lengthgen/pretrained_selector_family_summary.md"
    )
    args = parser.parse_args()
    paths = []
    for pattern in args.inputs:
        paths.extend(glob.glob(pattern) or [pattern])
    results = [json.loads(Path(path).read_text()) for path in sorted(set(paths))]
    summary = family_aggregate(results)
    Path(args.json_output).write_text(json.dumps(summary, indent=2) + "\n")
    Path(args.md_output).write_text(markdown(summary))
    print(f"wrote {args.json_output}")
    print(f"wrote {args.md_output}")


if __name__ == "__main__":
    main()
