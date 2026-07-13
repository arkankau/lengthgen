from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from thermosafety.thermo import binned_means, risk_bins, summarize_transition


def read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(rows: list[dict[str, object]], path: str | Path, fieldnames: list[str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def svg_line_plot(
    rows: list[dict[str, object]],
    path: str | Path,
    y_key: str,
    title: str,
    y_label: str,
) -> None:
    width, height = 760, 430
    margin = 58
    xs = [float(row["bin_mid"]) for row in rows if float(row["count"]) > 0]
    ys = [float(row[y_key]) for row in rows if float(row["count"]) > 0]
    if not xs:
        return
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(0.0, min(ys)), max(1.0, max(ys))
    if x_max <= x_min:
        x_max = x_min + 1e-6
    if y_max <= y_min:
        y_max = y_min + 1e-6

    def x_map(value: float) -> float:
        return margin + (value - x_min) / (x_max - x_min) * (width - 2 * margin)

    def y_map(value: float) -> float:
        return height - margin - (value - y_min) / (y_max - y_min) * (height - 2 * margin)

    points = " ".join(f"{x_map(x):.1f},{y_map(y):.1f}" for x, y in zip(xs, ys))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width/2}" y="28" text-anchor="middle" font-family="Arial" font-size="18">{title}</text>',
        f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="#111827"/>',
        f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" stroke="#111827"/>',
        f'<text x="{width/2}" y="{height-14}" text-anchor="middle" font-family="Arial" font-size="13">R(X)</text>',
        f'<text x="16" y="{height/2}" transform="rotate(-90 16 {height/2})" text-anchor="middle" font-family="Arial" font-size="13">{y_label}</text>',
        f'<polyline points="{points}" fill="none" stroke="#0f766e" stroke-width="3"/>',
    ]
    for x, y in zip(xs, ys):
        parts.append(f'<circle cx="{x_map(x):.1f}" cy="{y_map(y):.1f}" r="4" fill="#0f766e"/>')
    for tick in np.linspace(x_min, x_max, 5):
        parts.append(f'<text x="{x_map(float(tick)):.1f}" y="{height-margin+19}" text-anchor="middle" font-family="Arial" font-size="11">{tick:.2f}</text>')
    for tick in np.linspace(y_min, y_max, 5):
        parts.append(f'<text x="{margin-8}" y="{y_map(float(tick))+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{tick:.2f}</text>')
    parts.append("</svg>")
    Path(path).write_text("\n".join(parts), encoding="utf-8")


def suite_curve_rows(rows: list[dict[str, str]], edges: np.ndarray) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    suites = sorted({row["suite"] for row in rows})
    for suite in suites:
        suite_rows = [row for row in rows if row["suite"] == suite]
        risks = np.array([float(row["risk"]) for row in suite_rows], dtype=float)
        values = np.array([float(row["m_null"]) for row in suite_rows], dtype=float)
        for binned in binned_means(risks, values, edges):
            output.append({"suite": suite, **binned})
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze phase-transition-like null-attractor behavior.")
    parser.add_argument("--diagnostics", default="results/toy_diagnostics_expanded.csv")
    parser.add_argument("--bins", type=int, default=8)
    parser.add_argument("--output-prefix", default="results/phase_transition")
    args = parser.parse_args()

    rows = read_rows(args.diagnostics)
    risks = np.array([float(row["risk"]) for row in rows], dtype=float)
    edges = risk_bins(risks, bins=args.bins)
    summary = summarize_transition(rows, bins=args.bins)

    m_bins = binned_means(risks, np.array([float(row["m_null"]) for row in rows]), edges)
    entropy_bins = binned_means(risks, np.array([float(row["entropy"]) for row in rows]), edges)
    gap_bins = binned_means(risks, np.array([float(row["spectral_gap"]) for row in rows]), edges)
    combined = []
    for m_row, e_row, g_row in zip(m_bins, entropy_bins, gap_bins):
        combined.append(
            {
                "bin_left": m_row["bin_left"],
                "bin_right": m_row["bin_right"],
                "bin_mid": m_row["bin_mid"],
                "count": int(m_row["count"]),
                "mean_m_null": m_row["mean"],
                "var_m_null": m_row["variance"],
                "mean_entropy": e_row["mean"],
                "mean_spectral_gap": g_row["mean"],
            }
        )

    prefix = Path(args.output_prefix)
    write_csv(
        combined,
        prefix.with_name(prefix.name + "_bins.csv"),
        ["bin_left", "bin_right", "bin_mid", "count", "mean_m_null", "var_m_null", "mean_entropy", "mean_spectral_gap"],
    )
    write_csv(
        suite_curve_rows(rows, edges),
        prefix.with_name(prefix.name + "_suite_curves.csv"),
        ["suite", "bin_left", "bin_right", "bin_mid", "count", "mean", "variance"],
    )
    svg_line_plot(combined, prefix.with_name(prefix.name + "_m_null_vs_risk.svg"), "mean_m_null", "Order Parameter Transition", "mean m_null")
    svg_line_plot(combined, prefix.with_name(prefix.name + "_susceptibility.svg"), "var_m_null", "Susceptibility Proxy", "var(m_null)")
    svg_line_plot(combined, prefix.with_name(prefix.name + "_entropy_vs_risk.svg"), "mean_entropy", "Attention Entropy Across Transition", "mean entropy")
    svg_line_plot(combined, prefix.with_name(prefix.name + "_spectral_gap_vs_risk.svg"), "mean_spectral_gap", "Spectral Gap Across Transition", "mean spectral gap")

    report = [
        "# Phase-Transition Analysis",
        "",
        "This report analyzes null-attractor behavior as a mechanism test. It does not claim a working LLM defense or an in-layer intervention.",
        "",
        f"- Diagnostics: `{args.diagnostics}`",
        f"- Estimated critical risk: {summary.critical_risk:.3f}",
        f"- Max finite slope d(m_null)/dR: {summary.max_slope:.3f}",
        f"- Susceptibility peak risk: {summary.susceptibility_peak_risk:.3f}",
        f"- Susceptibility proxy peak var(m_null): {summary.susceptibility_peak:.4f}",
        f"- Low-risk mean m_null: {summary.low_risk_m_null:.3f}",
        f"- High-risk mean m_null: {summary.high_risk_m_null:.3f}",
        f"- Order-parameter jump: {summary.jump:.3f}",
        f"- Suite universality gap: {summary.universality_gap:.3f}",
        "",
        "## Artifacts",
        "",
        f"- `{prefix.with_name(prefix.name + '_bins.csv')}`",
        f"- `{prefix.with_name(prefix.name + '_suite_curves.csv')}`",
        f"- `{prefix.with_name(prefix.name + '_m_null_vs_risk.svg')}`",
        f"- `{prefix.with_name(prefix.name + '_susceptibility.svg')}`",
        f"- `{prefix.with_name(prefix.name + '_entropy_vs_risk.svg')}`",
        f"- `{prefix.with_name(prefix.name + '_spectral_gap_vs_risk.svg')}`",
        "",
        "## Interpretation Guardrail",
        "",
        "The key claim to test is not threshold classification. The relevant evidence is whether `m_null` behaves like an order parameter as `R(X)` crosses a critical region, and whether entropy/spectral-gap changes are consistent with collapse into an absorbing null basin.",
    ]
    prefix.with_name(prefix.name + "_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"wrote phase-transition analysis with prefix {prefix}")


if __name__ == "__main__":
    main()
