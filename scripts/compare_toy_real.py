from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def summarize(rows: list[dict[str, str]], source: str) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["suite"]].append(row)
    out = []
    for suite in sorted(grouped):
        suite_rows = grouped[suite]
        out.append(
            {
                "source": source,
                "suite": suite,
                "n": len(suite_rows),
                "mean_risk": mean([float(r["risk"]) for r in suite_rows]),
                "mean_m_null": mean([float(r["m_null"]) for r in suite_rows]),
                "collapse_rate": mean([float(r["collapsed"]) for r in suite_rows]),
                "entropy": mean([float(r["entropy"]) for r in suite_rows]),
                "spectral_gap": mean([float(r["spectral_gap"]) for r in suite_rows]),
            }
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare toy embeddings with real hidden-state diagnostics.")
    parser.add_argument("--toy", default="results/toy_diagnostics.csv")
    parser.add_argument("--real", default="results/hf_diagnostics.csv")
    parser.add_argument("--output", default="results/toy_vs_real_report.md")
    args = parser.parse_args()

    toy_rows = read_rows(args.toy)
    real_rows = read_rows(args.real)
    summary = summarize(toy_rows, "toy") + summarize(real_rows, "real_hidden")

    lines = [
        "# Toy vs Real Hidden-State Diagnostics",
        "",
        "This comparison is post-hoc diagnostic analysis. It does not patch model attention logits or demonstrate a generation-time defense.",
        "",
        "| source | suite | n | mean risk | mean m_null | collapse rate | entropy | spectral gap |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['source']} | {row['suite']} | {row['n']} | {row['mean_risk']:.3f} | "
            f"{row['mean_m_null']:.3f} | {row['collapse_rate']:.3f} | "
            f"{row['entropy']:.3f} | {row['spectral_gap']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The useful question is whether the same risk-conditioned null mass ordering appears when the query/key/value states come from an actual language model rather than deterministic toy embeddings.",
            "",
            "If separation weakens on real hidden states, the next step is to replace the heuristic risk score with a learned trajectory probe using hidden-state drift, unsafe-direction alignment, native attention entropy, and instruction-conflict features.",
        ]
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
