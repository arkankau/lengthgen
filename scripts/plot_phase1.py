from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_svg_scatter(rows: list[dict[str, str]], path: str | Path) -> None:
    width, height = 720, 420
    margin = 54
    colors = {
        "benign": "#2563eb",
        "benign_complex": "#0891b2",
        "direct_jailbreak": "#dc2626",
        "obfuscated_jailbreak": "#d97706",
        "long_context_jailbreak": "#7c3aed",
    }

    def x(v: float) -> float:
        return margin + v * (width - 2 * margin)

    def y(v: float) -> float:
        return height - margin - v * (height - 2 * margin)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="#111827"/>',
        f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" stroke="#111827"/>',
        f'<text x="{width/2}" y="28" text-anchor="middle" font-family="Arial" font-size="18">Null mass versus risk</text>',
        f'<text x="{width/2}" y="{height-12}" text-anchor="middle" font-family="Arial" font-size="13">R(X)</text>',
        f'<text x="16" y="{height/2}" transform="rotate(-90 16 {height/2})" text-anchor="middle" font-family="Arial" font-size="13">m_null</text>',
    ]
    for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
        parts.append(f'<line x1="{x(tick):.1f}" y1="{height-margin}" x2="{x(tick):.1f}" y2="{height-margin+5}" stroke="#111827"/>')
        parts.append(f'<text x="{x(tick):.1f}" y="{height-margin+20}" text-anchor="middle" font-family="Arial" font-size="11">{tick:.2f}</text>')
        parts.append(f'<line x1="{margin-5}" y1="{y(tick):.1f}" x2="{margin}" y2="{y(tick):.1f}" stroke="#111827"/>')
        parts.append(f'<text x="{margin-9}" y="{y(tick)+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{tick:.2f}</text>')

    for row in rows:
        suite = row["suite"]
        parts.append(
            f'<circle cx="{x(float(row["risk"])):.1f}" cy="{y(float(row["m_null"])):.1f}" r="5" '
            f'fill="{colors.get(suite, "#374151")}" opacity="0.82"><title>{suite}: {row["id"]}</title></circle>'
        )

    lx, ly = width - 230, 66
    for i, (suite, color) in enumerate(colors.items()):
        yy = ly + i * 20
        parts.append(f'<circle cx="{lx}" cy="{yy}" r="5" fill="{color}"/>')
        parts.append(f'<text x="{lx+12}" y="{yy+4}" font-family="Arial" font-size="12">{suite}</text>')
    parts.append("</svg>")
    Path(path).write_text("\n".join(parts), encoding="utf-8")


def write_svg_bars(rows: list[dict[str, str]], path: str | Path, value_key: str, title: str) -> None:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[row["suite"]].append(float(row[value_key]))
    suites = sorted(grouped)
    values = [sum(grouped[s]) / len(grouped[s]) for s in suites]

    width, height = 720, 420
    margin = 60
    bar_gap = 18
    bar_width = (width - 2 * margin - bar_gap * (len(suites) - 1)) / len(suites)

    def y(v: float) -> float:
        return height - margin - v * (height - 2 * margin)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width/2}" y="28" text-anchor="middle" font-family="Arial" font-size="18">{title}</text>',
        f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="#111827"/>',
        f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" stroke="#111827"/>',
    ]
    for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
        parts.append(f'<line x1="{margin-5}" y1="{y(tick):.1f}" x2="{margin}" y2="{y(tick):.1f}" stroke="#111827"/>')
        parts.append(f'<text x="{margin-9}" y="{y(tick)+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{tick:.2f}</text>')
    for i, (suite, value) in enumerate(zip(suites, values)):
        x0 = margin + i * (bar_width + bar_gap)
        y0 = y(value)
        parts.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{bar_width:.1f}" height="{height-margin-y0:.1f}" fill="#0f766e"/>')
        parts.append(f'<text x="{x0+bar_width/2:.1f}" y="{y0-6:.1f}" text-anchor="middle" font-family="Arial" font-size="11">{value:.2f}</text>')
        parts.append(f'<text x="{x0+bar_width/2:.1f}" y="{height-margin+14}" text-anchor="middle" font-family="Arial" font-size="10">{suite}</text>')
    parts.append("</svg>")
    Path(path).write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create dependency-free SVG plots for Phase 1.")
    parser.add_argument("--diagnostics", default="results/toy_diagnostics.csv")
    parser.add_argument("--output-dir", default="results/figures")
    args = parser.parse_args()

    rows = read_rows(args.diagnostics)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_svg_scatter(rows, out / "m_null_vs_risk.svg")
    write_svg_bars(rows, out / "collapse_rate_by_suite.svg", "collapsed", "Collapse rate by suite")
    write_svg_bars(rows, out / "entropy_by_suite.svg", "entropy", "Mean attention entropy by suite")
    write_svg_bars(rows, out / "spectral_gap_by_suite.svg", "spectral_gap", "Mean spectral gap by suite")
    print(f"wrote figures to {out}")


if __name__ == "__main__":
    main()
