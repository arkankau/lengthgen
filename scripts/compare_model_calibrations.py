from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def best_by_source(path: str | Path, model_label: str) -> list[dict[str, object]]:
    rows = read_rows(path)
    sources = sorted({row["risk_source"] for row in rows})
    best = []
    for source in sources:
        source_rows = [row for row in rows if row["risk_source"] == source]
        row = sorted(
            source_rows,
            key=lambda r: (float(r["score"]), float(r["jailbreak_collapse"])),
            reverse=True,
        )[0]
        best.append(
            {
                "model": model_label,
                "risk_source": source,
                "score": float(row["score"]),
                "benign_collapse": float(row.get("benign_collapse", 0.0)),
                "benign_complex_collapse": float(row["benign_complex_collapse"]),
                "jailbreak_collapse": float(row["jailbreak_collapse"]),
                "mean_m_null_benign_complex": float(row["mean_m_null_benign_complex"]),
                "mean_m_null_jailbreak": float(row["mean_m_null_jailbreak"]),
                "risk_threshold": float(row["risk_threshold"]),
                "eta_null": float(row["eta_null"]),
                "kappa": float(row["kappa"]),
                "normalize_hidden": int(float(row.get("normalize_hidden", 0))),
            }
        )
    return best


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare best calibration rows across model runs.")
    parser.add_argument("--tiny", default="results/hf_calibration_summary_expanded.csv")
    parser.add_argument("--distil-normalized", default="results/hf_calibration_summary_distilgpt2_normalized_expanded.csv")
    parser.add_argument("--output", default="results/model_calibration_comparison.md")
    args = parser.parse_args()

    rows = (
        best_by_source(args.tiny, "tiny-gpt2")
        + best_by_source(args.distil_normalized, "distilgpt2-normalized")
    )
    lines = [
        "# Model Calibration Comparison",
        "",
        "Best setting per risk source. These are post-hoc diagnostics, not in-layer generation interventions.",
        "",
        "| model | risk source | score | benign collapse | benign-complex collapse | jailbreak collapse | mean m_null benign-complex | mean m_null jailbreak | R_c | eta | kappa | normalized |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['model']} | {row['risk_source']} | {row['score']:.2f} | "
            f"{row['benign_collapse']:.2f} | {row['benign_complex_collapse']:.2f} | "
            f"{row['jailbreak_collapse']:.2f} | {row['mean_m_null_benign_complex']:.3f} | "
            f"{row['mean_m_null_jailbreak']:.3f} | {row['risk_threshold']:.2f} | "
            f"{row['eta_null']:.1f} | {row['kappa']:.1f} | {row['normalize_hidden']} |"
        )
    lines.extend(
        [
            "",
            "## Takeaway",
            "",
            "Expanding the prompt suite makes the task harder. Surface and mixed risk remain strongest, while latent-only probes still over-collapse benign safety-research prompts and miss paraphrased or many-shot adversarial prompts.",
        ]
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
