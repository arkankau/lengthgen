from __future__ import annotations

import argparse
import re
from pathlib import Path


METRIC_PATTERNS = {
    "critical_risk": r"Estimated critical risk: ([\-0-9.]+)",
    "max_slope": r"Max finite slope d\(m_null\)/dR: ([\-0-9.]+)",
    "susceptibility_peak": r"Susceptibility proxy peak var\(m_null\): ([\-0-9.]+)",
    "low_risk_m_null": r"Low-risk mean m_null: ([\-0-9.]+)",
    "high_risk_m_null": r"High-risk mean m_null: ([\-0-9.]+)",
    "jump": r"Order-parameter jump: ([\-0-9.]+)",
    "universality_gap": r"Suite universality gap: ([\-0-9.]+)",
}


def parse_report(path: str | Path) -> dict[str, float]:
    text = Path(path).read_text(encoding="utf-8")
    values = {}
    for key, pattern in METRIC_PATTERNS.items():
        match = re.search(pattern, text)
        values[key] = float(match.group(1)) if match else 0.0
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare phase-transition summaries.")
    parser.add_argument("--toy", default="results/phase_transition_toy_expanded_report.md")
    parser.add_argument("--tiny", default="results/phase_transition_tinygpt2_expanded_report.md")
    parser.add_argument("--distil", default="results/phase_transition_distilgpt2_normalized_expanded_report.md")
    parser.add_argument("--output", default="results/phase_transition_comparison.md")
    args = parser.parse_args()

    rows = [
        ("toy", parse_report(args.toy)),
        ("tiny-gpt2 diagnostic", parse_report(args.tiny)),
        ("distilgpt2 normalized diagnostic", parse_report(args.distil)),
    ]
    lines = [
        "# Phase-Transition Comparison",
        "",
        "This table compares mechanism-test evidence across toy embeddings and post-hoc real hidden-state diagnostics. It is not an in-layer intervention result.",
        "",
        "| setting | critical R | max slope | susceptibility peak | low-risk m_null | high-risk m_null | jump | universality gap |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, values in rows:
        lines.append(
            f"| {name} | {values['critical_risk']:.3f} | {values['max_slope']:.3f} | "
            f"{values['susceptibility_peak']:.4f} | {values['low_risk_m_null']:.3f} | "
            f"{values['high_risk_m_null']:.3f} | {values['jump']:.3f} | {values['universality_gap']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            "The toy mechanism shows the intended order-parameter jump. The tiny-GPT2 diagnostic does not. The normalized distilGPT2 diagnostic shows a steep transition but starts with excessive low-risk null mass, so it is not yet a useful defense-like operating point.",
        ]
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
