"""Analyze saved controlled utility-audit records without rerunning a model."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
PRIMARY_INPUT = REPO_ROOT / "results/lengthgen/utility_gap/routing_utility_gap_results.json"
RELEASE_INPUT = REPO_ROOT / "results/routing_utility_gap_results.json"
IS_RELEASE = not PRIMARY_INPUT.exists() and RELEASE_INPUT.exists()


def fit(x, y):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    slope, intercept = np.polyfit(x, y, 1)
    residual = y - (slope * x + intercept)
    return {
        "n": int(len(x)),
        "pearson": float(np.corrcoef(x, y)[0, 1]),
        "slope": float(slope),
        "intercept": float(intercept),
        "mae": float(np.abs(residual).mean()),
    }


def quantile_bins(total_transfer, actual, bins=4):
    total_transfer = np.asarray(total_transfer, dtype=np.float64)
    actual = np.asarray(actual, dtype=np.float64)
    edges = np.quantile(total_transfer, np.linspace(0.0, 1.0, bins + 1))
    rows = []
    for index in range(bins):
        low, high = edges[index], edges[index + 1]
        mask = (total_transfer >= low) & (
            total_transfer <= high if index == bins - 1 else total_transfer < high
        )
        rows.append({
            "quantile": f"Q{index + 1}",
            "n_examples": int(mask.sum()),
            "transfer_interval": [float(low), float(high)],
            "mean_total_transfer": float(total_transfer[mask].mean()),
            "mean_actual_margin_change": float(actual[mask].mean()),
            "positive_effect_fraction": float(np.mean(actual[mask] > 0)),
        })
    return rows


def save_figure(head_transfer, total_transfer, actual, rows, path):
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.55))
    axes[0].hist(head_transfer, bins=40, color="#011F5B", edgecolor="white")
    axes[0].set_xlabel(r"per-head transferred mass $\delta_h$")
    axes[0].set_ylabel("head-example pairs")
    axes[0].set_title("(a) Source-max displacement")
    axes[0].grid(alpha=0.2, axis="y")

    centers = np.arange(len(rows))
    means = [row["mean_actual_margin_change"] for row in rows]
    axes[1].bar(centers, means, color="#011F5B")
    axes[1].axhline(0.0, color="#555555", linewidth=0.8)
    axes[1].set_xticks(centers, [row["quantile"] for row in rows])
    axes[1].set_xlabel(r"total transfer $\sum_h\delta_h$ quantile")
    axes[1].set_ylabel("mean exact margin change")
    axes[1].set_title("(b) Effect by displacement")
    axes[1].grid(alpha=0.2, axis="y")
    fig.tight_layout(pad=0.6)
    fig.savefig(path, dpi=600, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=RELEASE_INPUT if IS_RELEASE else PRIMARY_INPUT,
    )
    parser.add_argument(
        "--out-json",
        default=(REPO_ROOT / "results/controlled_utility_audit.json") if IS_RELEASE else (REPO_ROOT / "results/lengthgen/controlled_utility_audit.json"),
    )
    parser.add_argument(
        "--out-report",
        default=(REPO_ROOT / "results/controlled_utility_audit.md") if IS_RELEASE else (REPO_ROOT / "results/lengthgen/controlled_utility_audit.md"),
    )
    parser.add_argument(
        "--out-figure",
        default=(REPO_ROOT / "figures/fig_controlled_delta_distribution.png") if IS_RELEASE else (REPO_ROOT / "paper_lengthgen_aaai/figures/fig_controlled_delta_distribution.png"),
    )
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text())
    records = payload["records"]
    predicted = [row["first_order_margin_change"] for row in records]
    actual = [row["actual_margin_change"] for row in records]
    head_transfer = [
        head["transfer_mass"]
        for row in records
        for head in row["heads"]
    ]
    total_transfer = [sum(head["transfer_mass"] for head in row["heads"]) for row in records]
    exact_argmax_fraction = float(np.mean(np.asarray(head_transfer) <= 1e-8))
    bins = quantile_bins(total_transfer, actual)
    groups = payload["summary"]["groups"]

    result = {
        "input": str(args.input),
        "n_examples": len(records),
        "n_head_example_pairs": len(head_transfer),
        "figure_point_regression": fit(
            [row["mean_first_order_change"] for row in groups],
            [row["mean_actual_change"] for row in groups],
        ),
        "per_example_regression": fit(predicted, actual),
        "per_head_transfer": {
            "exact_source_argmax_fraction": exact_argmax_fraction,
            "median": float(np.median(head_transfer)),
            "p90": float(np.quantile(head_transfer, 0.90)),
        },
        "per_example_total_transfer": {
            "median": float(np.median(total_transfer)),
            "p90": float(np.quantile(total_transfer, 0.90)),
            "effect_by_quartile": bins,
        },
    }

    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(result, indent=2) + "\n")
    figure_path = Path(args.out_figure)
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    save_figure(head_transfer, total_transfer, actual, bins, figure_path)

    point = result["figure_point_regression"]
    head = result["per_head_transfer"]
    lines = [
        "# Controlled Utility Audit",
        "",
        f"Figure-4b point regression: actual = {point['slope']:.3f} * predicted "
        f"+ {point['intercept']:+.3f} (n={point['n']}, Pearson={point['pearson']:.3f}).",
        f"Across {result['n_head_example_pairs']} head-example pairs, "
        f"{head['exact_source_argmax_fraction']:.1%} have zero source-max displacement; "
        f"median per-head delta is {head['median']:.3f} and P90 is {head['p90']:.3f}.",
        "",
        "| Total-transfer quartile | n | Mean total transfer | Mean exact margin change | Positive-effect fraction |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in bins:
        lines.append(
            f"| {row['quantile']} | {row['n_examples']} | {row['mean_total_transfer']:.3f} | "
            f"{row['mean_actual_margin_change']:+.3f} | {row['positive_effect_fraction']:.1%} |"
        )
    Path(args.out_report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_report).write_text("\n".join(lines) + "\n")
    print(f"Wrote {args.out_report} and {args.out_figure}")


if __name__ == "__main__":
    main()
