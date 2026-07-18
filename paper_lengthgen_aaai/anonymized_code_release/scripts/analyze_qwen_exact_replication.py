"""Aggregate exact matched Qwen routing replications across calibration seeds."""
from __future__ import annotations

import argparse
import glob
import itertools
import json
from pathlib import Path

import numpy as np


def exact_sign_flip(values):
    values = np.asarray(values, dtype=np.float64)
    observed = abs(float(values.mean()))
    null = [
        abs(float(np.mean(values * np.asarray(signs))))
        for signs in itertools.product((-1.0, 1.0), repeat=len(values))
    ]
    return float(np.mean(np.asarray(null) >= observed - 1e-12))


def hierarchical_interval(groups, seed=918_000, draws=20_000):
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(draws):
        selected = rng.integers(0, len(groups), size=len(groups))
        values = []
        for index in selected:
            group = np.asarray(groups[index], dtype=np.float64)
            values.append(group[rng.integers(0, len(group), size=len(group))].mean())
        means.append(np.mean(values))
    return [float(value) for value in np.quantile(means, [0.025, 0.975])]


def seed_effect(payload):
    margin, accuracy = [], []
    lengths = {}
    for length_text, cell in sorted(payload["lengths"].items(), key=lambda row: int(row[0])):
        source = cell["conditions"]["source_max"]["records"]
        control = cell["conditions"]["distractor_control"]["records"]
        current_margin = np.asarray([
            source[index]["margin"] - row["margin"] for index, row in enumerate(control)
        ], dtype=np.float64)
        current_accuracy = np.asarray([
            source[index]["correct"] - row["correct"] for index, row in enumerate(control)
        ], dtype=np.float64)
        margin.extend(current_margin.tolist())
        accuracy.extend(current_accuracy.tolist())
        lengths[length_text] = {
            "n": len(current_margin),
            "mean_margin": float(current_margin.mean()),
            "mean_accuracy": float(current_accuracy.mean()),
        }
    return np.asarray(margin), np.asarray(accuracy), lengths


def aggregate(
    payloads,
    expected_seeds=tuple(range(6)),
    original_seed=0,
    prospective_seeds=(1, 2, 3, 4, 5),
):
    rows = []
    margin_groups, accuracy_groups = [], []
    for payload in sorted(payloads, key=lambda row: int(row["seed"])):
        margin, accuracy, lengths = seed_effect(payload)
        margin_groups.append(margin)
        accuracy_groups.append(accuracy)
        rows.append({
            "seed": int(payload["seed"]),
            "dtype": payload["dtype"],
            "selection_length": int(payload["selection_length"]),
            "selected_layer": int(payload["selected_layer"]),
            "selected_heads": payload["selected_heads"],
            "lengths": lengths,
            "mean_margin": float(margin.mean()),
            "mean_accuracy": float(accuracy.mean()),
        })
    seed_means = [row["mean_margin"] for row in rows]
    available = [row["seed"] for row in rows]
    exact_p = exact_sign_flip(seed_means) if seed_means else float("nan")
    complete = set(expected_seeds).issubset(available)
    prospective_rows = [row for row in rows if row["seed"] in prospective_seeds]
    prospective_means = [row["mean_margin"] for row in prospective_rows]
    prospective_complete = set(prospective_seeds).issubset(available)
    original_rows = [row for row in rows if row["seed"] == original_seed]
    return {
        "protocol": "exact_headline_qwen_replication",
        "expected_seeds": list(expected_seeds),
        "available_seeds": available,
        "missing_seeds": sorted(set(expected_seeds) - set(available)),
        "original_seed": original_seed,
        "prospective_seeds": list(prospective_seeds),
        "setup_match": {
            "model": "Qwen/Qwen2.5-1.5B",
            "dtype": "torch.bfloat16",
            "selection_length": 5,
            "lengths": [5, 20, 80, 160],
            "examples_per_length": 128,
            "contrast": "source_max minus distractor_control",
        },
        "seeds": rows,
        "margin": {
            "mean": float(np.mean(seed_means)) if seed_means else float("nan"),
            "hierarchical_ci95": hierarchical_interval(margin_groups) if margin_groups else [float("nan")] * 2,
            "seed_means": seed_means,
            "exact_sign_flip_p": exact_p,
        },
        "original_result": {
            "available": bool(original_rows),
            "mean_margin": original_rows[0]["mean_margin"] if original_rows else float("nan"),
        },
        "new_seed_replication": {
            "complete": prospective_complete,
            "mean": float(np.mean(prospective_means)) if prospective_means else float("nan"),
            "seed_means": prospective_means,
            "all_positive": bool(
                prospective_complete and all(value > 0 for value in prospective_means)
            ),
            "exact_sign_flip_p": (
                exact_sign_flip(prospective_means) if prospective_means else float("nan")
            ),
            "note": (
                "With five prospective seeds, the smallest attainable two-sided exact "
                "sign-flip p-value is 0.0625."
            ),
        },
        "accuracy": {
            "mean": float(np.mean([row["mean_accuracy"] for row in rows])) if rows else float("nan"),
            "hierarchical_ci95": hierarchical_interval(accuracy_groups, 919_000) if accuracy_groups else [float("nan")] * 2,
        },
        "prospective_success": bool(
            complete and all(value > 0 for value in seed_means) and exact_p < 0.05
        ),
    }


def markdown(summary):
    prospective = summary["new_seed_replication"]
    lines = [
        "# Exact Qwen Replication",
        "",
        f"Available seeds: `{summary['available_seeds']}`; missing: `{summary['missing_seeds']}`.",
        f"Original seed-{summary['original_seed']} margin: "
        f"**{summary['original_result']['mean_margin']:+.3f}**.",
        f"Five new-seed mean: **{prospective['mean']:+.3f}**; "
        f"all positive: **{'yes' if prospective['all_positive'] else 'no'}**; "
        f"new-seed-only exact p: **{prospective['exact_sign_flip_p']:.6g}**.",
        prospective["note"],
        f"Mean source-max minus control margin: **{summary['margin']['mean']:+.3f}** "
        f"(hierarchical 95% CI [{summary['margin']['hierarchical_ci95'][0]:+.3f}, "
        f"{summary['margin']['hierarchical_ci95'][1]:+.3f}]).",
        f"Exact seed-level sign-flip p: **{summary['margin']['exact_sign_flip_p']:.6g}**.",
        f"Prospective success: **{'pass' if summary['prospective_success'] else 'pending/fail'}**.",
        "",
        "| Seed | Layer | Heads | Mean margin | Mean accuracy |",
        "|---:|---:|:---|---:|---:|",
    ]
    for row in summary["seeds"]:
        lines.append(
            f"| {row['seed']} | {row['selected_layer']} | {row['selected_heads']} | "
            f"{row['mean_margin']:+.3f} | {row['mean_accuracy']:+.3f} |"
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="*", default=[
        "results/lengthgen/pretrained_causal_qwen1p5b/pretrained_causal_routing_results.json",
        "results/lengthgen/pretrained_causal_qwen_exact_s*/pretrained_causal_routing_results.json",
    ])
    parser.add_argument("--json-output", default="results/lengthgen/qwen_exact_replication_summary.json")
    parser.add_argument("--md-output", default="results/lengthgen/qwen_exact_replication_summary.md")
    args = parser.parse_args()
    paths = []
    for pattern in args.inputs:
        paths.extend(glob.glob(pattern) or ([pattern] if Path(pattern).exists() else []))
    payloads = [json.loads(Path(path).read_text()) for path in sorted(set(paths))]
    summary = aggregate(payloads)
    Path(args.json_output).write_text(json.dumps(summary, indent=2) + "\n")
    Path(args.md_output).write_text(markdown(summary))
    print(Path(args.md_output).read_text())


if __name__ == "__main__":
    main()
