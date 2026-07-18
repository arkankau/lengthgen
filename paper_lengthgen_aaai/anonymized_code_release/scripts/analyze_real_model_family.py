"""Compare real-model recall probes across model families and head counts.

Usage:
  .venv/Scripts/python.exe scripts/analyze_real_model_family.py \
      results/lengthgen/realmodel_pythia1p4b_h8.json \
      results/lengthgen/realmodel_qwen1p5b_h8.json

Each input is produced by colab/real_model_probe.py.
The script writes a compact CSV and Markdown table under results/lengthgen/.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

OUT = Path("results/lengthgen")


def corr(x: list[float], y: list[float]) -> float:
    xx = np.array(x, dtype=float)
    yy = np.array(y, dtype=float)
    if len(xx) < 2 or np.std(xx) <= 1e-9 or np.std(yy) <= 1e-9:
        return float("nan")
    return float(np.corrcoef(xx, yy)[0, 1])


def within_length_mean(records: list[dict], key: str) -> tuple[float, int]:
    by_n: dict[int, list[dict]] = defaultdict(list)
    for row in records:
        by_n[int(row["N"])].append(row)
    values = []
    for rows in by_n.values():
        c = [float(row["correct"]) for row in rows]
        x = [float(row[key]) for row in rows]
        r = corr(x, c)
        if not np.isnan(r):
            values.append(r)
    return (float(np.mean(values)) if values else float("nan"), len(values))


def summarize(path: str | Path) -> dict[str, object]:
    data = json.loads(Path(path).read_text())
    records = data["records"]
    ns = sorted({int(row["N"]) for row in records})
    by_n = {n: [row for row in records if int(row["N"]) == n] for n in ns}
    acc = [float(np.mean([row["correct"] for row in by_n[n]])) for n in ns]
    attn = [float(np.mean([row["a_js"] for row in by_n[n]])) for n in ns]
    max_attn = [float(np.mean([row.get("a_js_max", float("nan")) for row in by_n[n]])) for n in ns]
    r_attn, k = within_length_mean(records, "a_js")
    r_norm, _ = within_length_mean(records, "normsq")
    r_ent, _ = within_length_mean(records, "entropy")
    return {
        "path": str(path),
        "model": data.get("model", ""),
        "heads": len(data.get("heads", [])),
        "n_examples": len(records),
        "lengths": ",".join(str(n) for n in ns),
        "acc_first": acc[0],
        "acc_last": acc[-1],
        "acc_drop": acc[0] - acc[-1],
        "attn_first": attn[0],
        "attn_last": attn[-1],
        "attn_drop": attn[0] - attn[-1],
        "all_head_attn_first": max_attn[0],
        "all_head_attn_last": max_attn[-1],
        "within_lengths": k,
        "within_corr_attn": r_attn,
        "within_corr_normsq": r_norm,
        "within_corr_neg_entropy": -r_ent if not np.isnan(r_ent) else float("nan"),
        "winner": max(
            [
                ("attn", r_attn),
                ("normsq", r_norm),
                ("neg_entropy", -r_ent if not np.isnan(r_ent) else float("nan")),
            ],
            key=lambda item: -999.0 if np.isnan(item[1]) else item[1],
        )[0],
    }


def fmt(value: object) -> str:
    if isinstance(value, float):
        if np.isnan(value):
            return ""
        return f"{value:.3f}"
    return str(value)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        "# Real-Model Family Robustness",
        "",
        "Each row is an in-context key-value recall probe.",
        "The primary statistic is the mean within-length point-biserial correlation with correctness.",
        "",
        "| model | heads | examples | lengths | acc drop | attn drop | corr attn | corr normsq | corr -entropy | winner |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['model']} | {row['heads']} | {row['n_examples']} | {row['lengths']} | "
            f"{fmt(row['acc_drop'])} | {fmt(row['attn_drop'])} | {fmt(row['within_corr_attn'])} | "
            f"{fmt(row['within_corr_normsq'])} | {fmt(row['within_corr_neg_entropy'])} | {row['winner']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(paths: list[str]) -> None:
    if not paths:
        raise SystemExit("provide one or more realmodel_results.json files")
    rows = [summarize(path) for path in paths]
    write_csv(OUT / "realmodel_family_summary.csv", rows)
    write_report(OUT / "realmodel_family_summary.md", rows)
    print((OUT / "realmodel_family_summary.md").as_posix())
    for row in rows:
        print(
            f"{row['model']} heads={row['heads']} acc_drop={fmt(row['acc_drop'])} "
            f"attn_drop={fmt(row['attn_drop'])} corr_attn={fmt(row['within_corr_attn'])} "
            f"corr_normsq={fmt(row['within_corr_normsq'])} corr_-entropy={fmt(row['within_corr_neg_entropy'])}"
        )


if __name__ == "__main__":
    main(sys.argv[1:])
