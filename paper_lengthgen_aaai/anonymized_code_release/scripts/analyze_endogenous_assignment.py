"""Aggregate endogenous prompt-permutation assignment bridges across seeds."""
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


def hierarchical_interval(groups, seed, draws=20_000):
    rng = np.random.default_rng(seed)
    output = []
    for _ in range(draws):
        selected = rng.integers(0, len(groups), size=len(groups))
        means = []
        for index in selected:
            group = np.asarray(groups[index], dtype=np.float64)
            means.append(group[rng.integers(0, len(group), size=len(group))].mean())
        output.append(np.mean(means))
    return [float(value) for value in np.quantile(output, [0.025, 0.975])]


def aggregate(payloads, expected_seeds=tuple(range(6))):
    seed_rows = []
    margin_groups = []
    for payload in sorted(payloads, key=lambda row: int(row["seed"])):
        pairs = [
            pair
            for cell in payload["lengths"].values()
            for pair in cell["matched_pairs"]
        ]
        margin = np.asarray([row["margin_delta"] for row in pairs], dtype=np.float64)
        coefficient = float(np.mean([
            cell["fixed_effects_coefficients"]["source_mass"]
            for cell in payload["lengths"].values()
        ]))
        margin_groups.append(margin)
        seed_rows.append({
            "seed": int(payload["seed"]),
            "selected_layer": payload["selected_layer"],
            "selected_heads": payload["selected_heads"],
            "eligible_pairs": len(pairs),
            "mean_margin_delta": float(margin.mean()),
            "positive_margin_fraction": float(np.mean(margin > 0)),
            "mean_source_coefficient": coefficient,
            "median_spectrum_l1": float(np.median([
                row["sorted_spectrum_l1"] for row in pairs
            ])),
            "median_source_gap": float(np.median([
                row["source_mass_delta"] for row in pairs
            ])),
        })
    available = [row["seed"] for row in seed_rows]
    seed_margin = [row["mean_margin_delta"] for row in seed_rows]
    seed_coefficient = [row["mean_source_coefficient"] for row in seed_rows]
    complete = set(expected_seeds).issubset(available)
    margin_ci = hierarchical_interval(margin_groups, 930_000) if margin_groups else [float("nan")] * 2
    return {
        "protocol": "endogenous_distractor_order_assignment",
        "expected_seeds": list(expected_seeds),
        "available_seeds": available,
        "missing_seeds": sorted(set(expected_seeds) - set(available)),
        "seeds": seed_rows,
        "matched_margin": {
            "mean": float(np.mean(seed_margin)) if seed_margin else float("nan"),
            "hierarchical_ci95": margin_ci,
            "seed_means": seed_margin,
            "exact_seed_sign_flip_p": exact_sign_flip(seed_margin) if seed_margin else float("nan"),
        },
        "fixed_effects_source_coefficient": {
            "mean": float(np.mean(seed_coefficient)) if seed_coefficient else float("nan"),
            "seed_values": seed_coefficient,
            "exact_seed_sign_flip_p": exact_sign_flip(seed_coefficient) if seed_coefficient else float("nan"),
        },
        "prospective_success": bool(
            complete
            and all(value > 0 for value in seed_margin)
            and all(value > 0 for value in seed_coefficient)
            and margin_ci[0] > 0
            and exact_sign_flip(seed_margin) < 0.05
        ),
    }


def markdown(summary):
    margin = summary["matched_margin"]
    coefficient = summary["fixed_effects_source_coefficient"]
    lines = [
        "# Endogenous Assignment Bridge",
        "",
        f"Available seeds: `{summary['available_seeds']}`; missing: `{summary['missing_seeds']}`.",
        f"Matched naturally produced margin difference: **{margin['mean']:+.3f}** "
        f"(hierarchical 95% CI [{margin['hierarchical_ci95'][0]:+.3f}, "
        f"{margin['hierarchical_ci95'][1]:+.3f}]; exact seed p={margin['exact_seed_sign_flip_p']:.6g}).",
        f"Within-base source-mass coefficient controlling maximum and entropy: "
        f"**{coefficient['mean']:+.3f}** (exact seed p={coefficient['exact_seed_sign_flip_p']:.6g}).",
        f"Prospective success: **{'pass' if summary['prospective_success'] else 'pending/fail'}**.",
        "",
        "| Seed | Layer | Eligible pairs | Margin delta | Positive | Source coefficient | Median spectrum L1 | Median source gap |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["seeds"]:
        lines.append(
            f"| {row['seed']} | {row['selected_layer']} | {row['eligible_pairs']} | "
            f"{row['mean_margin_delta']:+.3f} | {row['positive_margin_fraction']:.1%} | "
            f"{row['mean_source_coefficient']:+.3f} | {row['median_spectrum_l1']:.4f} | "
            f"{row['median_source_gap']:.4f} |"
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="*", default=[
        "results/lengthgen/pretrained_endogenous_assignment_s*/pretrained_endogenous_assignment_results.json"
    ])
    parser.add_argument("--json-output", default="results/lengthgen/endogenous_assignment_summary.json")
    parser.add_argument("--md-output", default="results/lengthgen/endogenous_assignment_summary.md")
    args = parser.parse_args()
    paths = []
    for pattern in args.inputs:
        paths.extend(glob.glob(pattern) or ([pattern] if Path(pattern).exists() else []))
    payloads = [json.loads(Path(path).read_text()) for path in sorted(set(paths))]
    if not payloads:
        raise SystemExit("no endogenous assignment results found")
    summary = aggregate(payloads)
    Path(args.json_output).write_text(json.dumps(summary, indent=2) + "\n")
    Path(args.md_output).write_text(markdown(summary))
    print(Path(args.md_output).read_text())


if __name__ == "__main__":
    main()
