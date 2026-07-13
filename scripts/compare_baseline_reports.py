from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_summary(path: str | Path, setting: str) -> list[dict[str, object]]:
    with Path(path).open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    output = []
    for row in rows:
        output.append(
            {
                "setting": setting,
                "method": row["method"],
                "jailbreak_collapse_rate": float(row["jailbreak_collapse_rate"]),
                "benign_false_collapse_rate": float(row["benign_false_collapse_rate"]),
                "max_slope": float(row["max_slope"]),
                "susceptibility_peak": float(row["susceptibility_peak"]),
                "low_risk_response": float(row["low_risk_response"]),
                "high_risk_response": float(row["high_risk_response"]),
                "jump": float(row["jump"]),
                "thermodynamic_observables": row["thermodynamic_observables"],
            }
        )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Combine threshold-baseline summaries.")
    parser.add_argument("--toy", default="results/baseline_comparison_toy_expanded_summary.csv")
    parser.add_argument("--tiny", default="results/baseline_comparison_tinygpt2_expanded_summary.csv")
    parser.add_argument("--distil", default="results/baseline_comparison_distilgpt2_normalized_expanded_summary.csv")
    parser.add_argument("--output", default="results/baseline_comparison_summary.md")
    args = parser.parse_args()

    rows = (
        read_summary(args.toy, "toy")
        + read_summary(args.tiny, "tiny-gpt2 diagnostic")
        + read_summary(args.distil, "distilgpt2 normalized diagnostic")
    )
    lines = [
        "# Baseline Comparison Summary",
        "",
        "Plain thresholding is a classification control. It does not patch attention logits or produce attention entropy/spectral-gap evidence of null-basin dynamics.",
        "",
        "| setting | method | jailbreak collapse | benign false collapse | max slope | susceptibility peak | low-risk response | high-risk response | jump | thermodynamic observables |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['setting']} | {row['method']} | {row['jailbreak_collapse_rate']:.3f} | "
            f"{row['benign_false_collapse_rate']:.3f} | {row['max_slope']:.3f} | "
            f"{row['susceptibility_peak']:.4f} | {row['low_risk_response']:.3f} | "
            f"{row['high_risk_response']:.3f} | {row['jump']:.3f} | {row['thermodynamic_observables']} |"
        )
    lines.extend(
        [
            "",
            "## Takeaway",
            "",
            "Thresholding can produce a sharper binary decision curve, but that is exactly why it is only a baseline. The null-attractor mechanism must be judged by whether it creates an attention-level order parameter with meaningful entropy and spectral-gap changes, not by whether it merely imitates `R(X) >= R_c`.",
        ]
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
