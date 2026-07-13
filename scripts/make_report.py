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


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def summarize(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["suite"]].append(row)
    summary = []
    for suite in sorted(grouped):
        suite_rows = grouped[suite]
        summary.append(
            {
                "suite": suite,
                "n": len(suite_rows),
                "mean_risk": mean([float(r["risk"]) for r in suite_rows]),
                "mean_m_null": mean([float(r["m_null"]) for r in suite_rows]),
                "collapse_rate": mean([float(r["collapsed"]) for r in suite_rows]),
                "entropy": mean([float(r["entropy"]) for r in suite_rows]),
                "spectral_gap": mean([float(r["spectral_gap"]) for r in suite_rows]),
            }
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Phase 1 markdown report.")
    parser.add_argument("--diagnostics", default="results/toy_diagnostics.csv")
    parser.add_argument("--threshold-sweep", default="results/threshold_sweep.csv")
    parser.add_argument("--ablation-sweep", default="results/ablation_sweep.csv")
    parser.add_argument("--output", default="results/phase1_report.md")
    args = parser.parse_args()

    rows = read_rows(args.diagnostics)
    summary = summarize(rows)
    benign_complex = next((r for r in summary if r["suite"] == "benign_complex"), None)
    direct = next((r for r in summary if r["suite"] == "direct_jailbreak"), None)

    lines = [
        "# Phase 1 Null-Attractor Toy Report",
        "",
        "This report summarizes a mechanism test, not a validated LLM defense. The toy risk functional changes the attention energy landscape, then `m_null` measures whether attention collapses into the appended null slot.",
        "",
        "## Operating Region",
        "",
    ]
    if benign_complex and direct:
        lines.append(
            f"At the default operating point, benign-complex collapse rate is {benign_complex['collapse_rate']:.2f}, "
            f"while direct-jailbreak collapse rate is {direct['collapse_rate']:.2f}."
        )
    lines.extend(
        [
            "",
            "| suite | n | mean risk | mean m_null | collapse rate | entropy | spectral gap |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary:
        lines.append(
            f"| {row['suite']} | {row['n']} | {row['mean_risk']:.3f} | {row['mean_m_null']:.3f} | "
            f"{row['collapse_rate']:.3f} | {row['entropy']:.3f} | {row['spectral_gap']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Figures",
            "",
            "- `results/figures/m_null_vs_risk.svg`",
            "- `results/figures/collapse_rate_by_suite.svg`",
            "- `results/figures/entropy_by_suite.svg`",
            "- `results/figures/spectral_gap_by_suite.svg`",
            "",
            "## Artifacts",
            "",
            f"- Diagnostics: `{args.diagnostics}`",
            f"- Risk-threshold sweep: `{args.threshold_sweep}`",
            f"- One-factor ablation sweep: `{args.ablation_sweep}`",
            "",
            "## Limitations",
            "",
            "- The current `R(X)` is a transparent heuristic and should be replaced by a latent trajectory probe.",
            "- Collapse here is diagnostic attention collapse, not an in-layer generation intervention.",
            "- Prompt examples are intentionally non-operational and benchmark-safe.",
        ]
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
