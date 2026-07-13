from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from thermosafety.thermo import binned_means, max_finite_slope, risk_bins, summarize_transition


def read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def label_is_jailbreak(row: dict[str, str]) -> bool:
    return row.get("label") == "jailbreak" or "jailbreak" in row.get("suite", "")


def threshold_predictions(rows: list[dict[str, str]], threshold: float) -> list[dict[str, str]]:
    output = []
    for row in rows:
        copied = dict(row)
        block = float(float(row["risk"]) >= threshold)
        copied["m_null"] = str(block)
        copied["collapsed"] = str(int(block))
        copied["entropy"] = "0.0"
        copied["spectral_gap"] = "0.0"
        output.append(copied)
    return output


def rates(rows: list[dict[str, str]], prediction_key: str = "collapsed") -> dict[str, float]:
    positives = [row for row in rows if label_is_jailbreak(row)]
    negatives = [row for row in rows if not label_is_jailbreak(row)]
    tpr = (
        sum(float(row[prediction_key]) >= 0.5 for row in positives) / len(positives)
        if positives
        else 0.0
    )
    fpr = (
        sum(float(row[prediction_key]) >= 0.5 for row in negatives) / len(negatives)
        if negatives
        else 0.0
    )
    return {"jailbreak_collapse_rate": float(tpr), "benign_false_collapse_rate": float(fpr)}


def best_threshold(rows: list[dict[str, str]]) -> float:
    risks = sorted({float(row["risk"]) for row in rows})
    candidates = [risks[0] - 1e-6]
    candidates.extend((a + b) / 2.0 for a, b in zip(risks, risks[1:]))
    candidates.append(risks[-1] + 1e-6)
    best = candidates[0]
    best_score = float("-inf")
    for threshold in candidates:
        pred_rows = threshold_predictions(rows, threshold)
        rate = rates(pred_rows)
        score = rate["jailbreak_collapse_rate"] - rate["benign_false_collapse_rate"]
        if score > best_score:
            best_score = score
            best = threshold
    return best


def binned_threshold_rows(rows: list[dict[str, str]], threshold: float, bins: int) -> list[dict[str, object]]:
    pred_rows = threshold_predictions(rows, threshold)
    risks = np.array([float(row["risk"]) for row in pred_rows], dtype=float)
    values = np.array([float(row["m_null"]) for row in pred_rows], dtype=float)
    edges = risk_bins(risks, bins=bins)
    return [
        {
            "baseline": "threshold",
            "bin_left": row["bin_left"],
            "bin_right": row["bin_right"],
            "bin_mid": row["bin_mid"],
            "count": int(row["count"]),
            "mean_response": row["mean"],
            "variance": row["variance"],
        }
        for row in binned_means(risks, values, edges)
    ]


def write_csv(rows: list[dict[str, object]], path: str | Path, fieldnames: list[str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def svg_compare_curves(
    null_rows: list[dict[str, object]],
    threshold_rows: list[dict[str, object]],
    path: str | Path,
) -> None:
    width, height = 760, 430
    margin = 58
    xs = [float(row["bin_mid"]) for row in null_rows + threshold_rows if int(row["count"]) > 0]
    ys = [float(row["mean_response"]) for row in null_rows + threshold_rows if int(row["count"]) > 0]
    if not xs:
        return
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = 0.0, max(1.0, max(ys))

    def x_map(value: float) -> float:
        return margin + (value - x_min) / (x_max - x_min + 1e-12) * (width - 2 * margin)

    def y_map(value: float) -> float:
        return height - margin - (value - y_min) / (y_max - y_min + 1e-12) * (height - 2 * margin)

    def points(rows: list[dict[str, object]]) -> str:
        selected = [row for row in rows if int(row["count"]) > 0]
        return " ".join(f"{x_map(float(row['bin_mid'])):.1f},{y_map(float(row['mean_response'])):.1f}" for row in selected)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width/2}" y="28" text-anchor="middle" font-family="Arial" font-size="18">Null Attractor vs Threshold Baseline</text>',
        f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="#111827"/>',
        f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" stroke="#111827"/>',
        f'<text x="{width/2}" y="{height-14}" text-anchor="middle" font-family="Arial" font-size="13">R(X)</text>',
        f'<text x="16" y="{height/2}" transform="rotate(-90 16 {height/2})" text-anchor="middle" font-family="Arial" font-size="13">mean response</text>',
        f'<polyline points="{points(null_rows)}" fill="none" stroke="#0f766e" stroke-width="3"/>',
        f'<polyline points="{points(threshold_rows)}" fill="none" stroke="#dc2626" stroke-width="3" stroke-dasharray="7 5"/>',
        f'<circle cx="{width-210}" cy="64" r="5" fill="#0f766e"/><text x="{width-196}" y="68" font-family="Arial" font-size="12">m_null</text>',
        f'<circle cx="{width-210}" cy="84" r="5" fill="#dc2626"/><text x="{width-196}" y="88" font-family="Arial" font-size="12">threshold block</text>',
    ]
    parts.append("</svg>")
    Path(path).write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare null-attractor diagnostics against a plain threshold baseline.")
    parser.add_argument("--diagnostics", default="results/toy_diagnostics_expanded.csv")
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--bins", type=int, default=8)
    parser.add_argument("--output-prefix", default="results/baseline_comparison")
    args = parser.parse_args()

    rows = read_rows(args.diagnostics)
    threshold = best_threshold(rows) if args.threshold is None else args.threshold
    threshold_rows = threshold_predictions(rows, threshold)

    null_summary = summarize_transition(rows, bins=args.bins)
    threshold_summary = summarize_transition(threshold_rows, bins=args.bins)
    null_rates = rates(rows)
    threshold_rates = rates(threshold_rows)

    risks = np.array([float(row["risk"]) for row in rows], dtype=float)
    edges = risk_bins(risks, bins=args.bins)
    null_curve = [
        {
            "baseline": "null_attractor",
            "bin_left": row["bin_left"],
            "bin_right": row["bin_right"],
            "bin_mid": row["bin_mid"],
            "count": int(row["count"]),
            "mean_response": row["mean"],
            "variance": row["variance"],
        }
        for row in binned_means(risks, np.array([float(row["m_null"]) for row in rows], dtype=float), edges)
    ]
    threshold_curve = binned_threshold_rows(rows, threshold, args.bins)

    prefix = Path(args.output_prefix)
    write_csv(
        null_curve + threshold_curve,
        prefix.with_name(prefix.name + "_curves.csv"),
        ["baseline", "bin_left", "bin_right", "bin_mid", "count", "mean_response", "variance"],
    )
    svg_compare_curves(null_curve, threshold_curve, prefix.with_name(prefix.name + "_curves.svg"))

    comparison_rows = [
        {
            "method": "null_attractor",
            "threshold": "",
            "jailbreak_collapse_rate": null_rates["jailbreak_collapse_rate"],
            "benign_false_collapse_rate": null_rates["benign_false_collapse_rate"],
            "critical_risk": null_summary.critical_risk,
            "max_slope": null_summary.max_slope,
            "susceptibility_peak": null_summary.susceptibility_peak,
            "low_risk_response": null_summary.low_risk_m_null,
            "high_risk_response": null_summary.high_risk_m_null,
            "jump": null_summary.jump,
            "thermodynamic_observables": "yes",
        },
        {
            "method": "threshold",
            "threshold": threshold,
            "jailbreak_collapse_rate": threshold_rates["jailbreak_collapse_rate"],
            "benign_false_collapse_rate": threshold_rates["benign_false_collapse_rate"],
            "critical_risk": threshold_summary.critical_risk,
            "max_slope": threshold_summary.max_slope,
            "susceptibility_peak": threshold_summary.susceptibility_peak,
            "low_risk_response": threshold_summary.low_risk_m_null,
            "high_risk_response": threshold_summary.high_risk_m_null,
            "jump": threshold_summary.jump,
            "thermodynamic_observables": "no",
        },
    ]
    write_csv(
        comparison_rows,
        prefix.with_name(prefix.name + "_summary.csv"),
        [
            "method",
            "threshold",
            "jailbreak_collapse_rate",
            "benign_false_collapse_rate",
            "critical_risk",
            "max_slope",
            "susceptibility_peak",
            "low_risk_response",
            "high_risk_response",
            "jump",
            "thermodynamic_observables",
        ],
    )

    report = [
        "# Threshold Baseline Comparison",
        "",
        "This compares the null-attractor diagnostic against a plain `R(X) >= R_c` threshold rule. The threshold baseline can classify/block, but it does not modify an attention energy landscape and has no attention entropy, spectral gap, or null-basin dynamics.",
        "",
        f"- Diagnostics: `{args.diagnostics}`",
        f"- Threshold baseline R_c: {threshold:.3f}",
        "",
        "| method | jailbreak collapse | benign false collapse | max slope | susceptibility peak | low-risk response | high-risk response | jump | thermodynamic observables |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in comparison_rows:
        report.append(
            f"| {row['method']} | {row['jailbreak_collapse_rate']:.3f} | {row['benign_false_collapse_rate']:.3f} | "
            f"{row['max_slope']:.3f} | {row['susceptibility_peak']:.4f} | {row['low_risk_response']:.3f} | "
            f"{row['high_risk_response']:.3f} | {row['jump']:.3f} | {row['thermodynamic_observables']} |"
        )
    report.extend(
        [
            "",
            "## Reading",
            "",
            "A threshold rule is an important control, but it is not the proposed mechanism. The relevant comparison is whether the null-attractor path provides order-parameter, entropy, and spectral-gap evidence of energy-landscape collapse rather than only a binary decision boundary.",
            "",
            "## Artifacts",
            "",
            f"- `{prefix.with_name(prefix.name + '_summary.csv')}`",
            f"- `{prefix.with_name(prefix.name + '_curves.csv')}`",
            f"- `{prefix.with_name(prefix.name + '_curves.svg')}`",
        ]
    )
    prefix.with_name(prefix.name + "_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"wrote baseline comparison with prefix {prefix}")


if __name__ == "__main__":
    main()
