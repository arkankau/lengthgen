"""Aggregate utility-selected interpolation and matched-control runs."""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np

from analyze_pretrained_utility_selection import hierarchical_interval


def contrast(result, alpha):
    row = result["dose_response"][str(alpha)]
    source = row["source_max"]["records"]
    control = row["matched_control"]["records"]
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
    }


def aggregate(results, expected_seeds=tuple(range(5))):
    ordered = sorted(results, key=lambda row: int(row["seed"]))
    available = [int(row["seed"]) for row in ordered]
    alphas = [float(value) for value in ordered[0]["alphas"]] if ordered else []
    rows = {}
    means = []
    for index, alpha in enumerate(alphas):
        groups = [contrast(result, alpha) for result in ordered]
        row = summarize_groups(groups, 300_000 + index)
        source_displacements = []
        control_displacements = []
        for result in ordered:
            current = result["dose_response"][str(alpha)]
            for name in ("source_max", "matched_control"):
                diagnostics = current[name].get("invariant_max_abs_error", {})
                count = diagnostics.get("displacement_count", 0)
                if count:
                    value = diagnostics["l1_displacement_sum"] / count
                    if name == "source_max":
                        source_displacements.append(value)
                    else:
                        control_displacements.append(value)
        row["mean_source_l1_displacement"] = (
            float(np.mean(source_displacements)) if source_displacements else None
        )
        row["mean_control_l1_displacement"] = (
            float(np.mean(control_displacements)) if control_displacements else None
        )
        row["mean_absolute_l1_mismatch"] = (
            float(np.mean(np.abs(
                np.asarray(source_displacements) - np.asarray(control_displacements)
            ))) if source_displacements else None
        )
        rows[str(alpha)] = row
        means.append(row["mean"])
    alpha_zero_exact = bool(not means or abs(means[0]) <= 1e-8)
    nondecreasing = bool(
        all(right + 1e-8 >= left for left, right in zip(means, means[1:]))
    )
    endpoint_positive = bool(
        alphas and rows[str(alphas[-1])]["ci95"][0] > 0
    )
    return {
        "expected_seeds": list(expected_seeds),
        "available_seeds": available,
        "missing_seeds": sorted(set(expected_seeds) - set(available)),
        "alphas": alphas,
        "dose_response": rows,
        "alpha_zero_numerically_zero": alpha_zero_exact,
        "mean_effect_nondecreasing": nondecreasing,
        "alpha_one_interval_positive": endpoint_positive,
        "preregistered_success": bool(
            alpha_zero_exact and nondecreasing and endpoint_positive
        ),
    }


def markdown_report(summary):
    lines = [
        "# Pretrained Dose-Response Summary",
        "",
        f"Preregistered success rule: **{'pass' if summary['preregistered_success'] else 'fail'}**.",
        f"Endpoint positive: `{summary['alpha_one_interval_positive']}`; "
        f"mean path nondecreasing: `{summary['mean_effect_nondecreasing']}`; "
        f"alpha zero: `{summary['alpha_zero_numerically_zero']}`.",
        f"Seeds: `{summary['available_seeds']}`; missing: `{summary['missing_seeds']}`.",
        "",
        "| Alpha | Source minus matched control | Hierarchical 95% CI | Source/control L1 | Seed means |",
        "|---:|---:|---:|---:|:---|",
    ]
    for alpha in summary["alphas"]:
        row = summary["dose_response"][str(alpha)]
        seed_means = ", ".join(f"{value:+.3f}" for value in row["seed_means"])
        lines.append(
            f"| {alpha:.2f} | {row['mean']:+.3f} | "
            f"[{row['ci95'][0]:+.3f}, {row['ci95'][1]:+.3f}] | "
            f"{row['mean_source_l1_displacement']:.3f}/"
            f"{row['mean_control_l1_displacement']:.3f} | {seed_means} |"
        )
    lines += [
        "",
        "The endpoint tests the established fixed-spectrum intervention. The interior "
        "alphas test whether the effect is a smooth routing response rather than an "
        "artifact that appears only after a maximal attention rewrite.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inputs", nargs="*",
        default=[
            "results/lengthgen/pretrained_dose_response_smollm2_s*/"
            "pretrained_dose_response_results.json"
        ],
    )
    parser.add_argument(
        "--json-output",
        default="results/lengthgen/pretrained_dose_response_summary.json",
    )
    parser.add_argument(
        "--md-output",
        default="results/lengthgen/pretrained_dose_response_summary.md",
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
