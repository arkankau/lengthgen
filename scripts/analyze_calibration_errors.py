from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    parser = argparse.ArgumentParser(description="List false collapses and missed jailbreak collapses.")
    parser.add_argument("--details", default="results/hf_calibration_best_details_expanded.csv")
    parser.add_argument("--output", default="results/hf_calibration_error_analysis.md")
    args = parser.parse_args()

    rows = read_rows(args.details)
    false_collapses = [
        row for row in rows
        if row["label"] != "jailbreak" and int(float(row["collapsed"])) == 1
    ]
    misses = [
        row for row in rows
        if row["label"] == "jailbreak" and int(float(row["collapsed"])) == 0
    ]

    lines = [
        "# HF Calibration Error Analysis",
        "",
        "This report inspects the best calibration setting selected by the sweep. It is prompt-level diagnostic analysis, not a generation-time safety evaluation.",
        "",
        f"- False benign collapses: {len(false_collapses)}",
        f"- Missed jailbreak collapses: {len(misses)}",
        "",
        "## False Benign Collapses",
        "",
        "| id | suite | risk | m_null | surface risk | probe risk |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in false_collapses:
        lines.append(
            f"| {row['id']} | {row['suite']} | {float(row['risk']):.3f} | {float(row['m_null']):.3f} | "
            f"{float(row['surface_risk']):.3f} | {float(row['probe_risk']):.3f} |"
        )

    lines.extend(
        [
            "",
            "## Missed Jailbreak Collapses",
            "",
            "| id | suite | risk | m_null | surface risk | probe risk |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in misses:
        lines.append(
            f"| {row['id']} | {row['suite']} | {float(row['risk']):.3f} | {float(row['m_null']):.3f} | "
            f"{float(row['surface_risk']):.3f} | {float(row['probe_risk']):.3f} |"
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
