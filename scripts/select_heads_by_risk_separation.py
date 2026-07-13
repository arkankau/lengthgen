from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


FIELDNAMES = [
    "layer",
    "head",
    "score",
    "separation",
    "jailbreak_m_null",
    "benign_m_null",
    "jailbreak_n",
    "benign_n",
]


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def rank_heads(rows: list[dict[str, str]], benign_penalty: float) -> list[dict[str, object]]:
    grouped: dict[tuple[int, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(int(float(row["layer"])), int(float(row["head"])))].append(row)

    ranked = []
    for (layer, head), group in grouped.items():
        jailbreak = [float(row["m_null"]) for row in group if row["label"] == "jailbreak"]
        benign = [float(row["m_null"]) for row in group if row["label"] == "benign"]
        if not jailbreak or not benign:
            continue
        jailbreak_mean = mean(jailbreak)
        benign_mean = mean(benign)
        separation = jailbreak_mean - benign_mean
        score = separation - benign_penalty * benign_mean
        ranked.append(
            {
                "layer": layer,
                "head": head,
                "score": score,
                "separation": separation,
                "jailbreak_m_null": jailbreak_mean,
                "benign_m_null": benign_mean,
                "jailbreak_n": len(jailbreak),
                "benign_n": len(benign),
            }
        )
    return sorted(ranked, key=lambda row: float(row["score"]), reverse=True)


def write_outputs(rows: list[dict[str, object]], csv_output: str | Path, report_output: str | Path, top_k: int) -> None:
    output = Path(csv_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Head Selection by Risk Separation",
        "",
        "Heads are ranked by jailbreak minus benign null mass, with a benign-null penalty. Use this to choose heads for the in-layer intervention instead of selecting only by layer.",
        "",
        "| rank | layer | head | score | separation | jailbreak m_null | benign m_null |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for idx, row in enumerate(rows[:top_k], start=1):
        lines.append(
            f"| {idx} | {row['layer']} | {row['head']} | {float(row['score']):.3f} | "
            f"{float(row['separation']):.3f} | {float(row['jailbreak_m_null']):.3f} | {float(row['benign_m_null']):.3f} |"
        )
    report = Path(report_output)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank intervention heads by measured null-mass risk separation.")
    parser.add_argument("--input", default="results/intervention_m_null_by_head.csv")
    parser.add_argument("--output", default="results/head_risk_separation.csv")
    parser.add_argument("--report-output", default="results/head_risk_separation.md")
    parser.add_argument("--benign-penalty", type=float, default=0.5)
    parser.add_argument("--top-k", type=int, default=16)
    args = parser.parse_args()

    ranked = rank_heads(read_rows(args.input), args.benign_penalty)
    write_outputs(ranked, args.output, args.report_output, args.top_k)
    print(f"wrote {len(ranked)} ranked heads to {args.output}")
    print(f"wrote report to {args.report_output}")


if __name__ == "__main__":
    main()
