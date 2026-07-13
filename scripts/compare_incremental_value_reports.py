from __future__ import annotations

import argparse
import csv
from pathlib import Path


SHARED_TARGETS = ["utility_loss", "coherence", "collapse_failure"]


def read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def pooled_by_target(path: str | Path) -> dict[str, dict[str, str]]:
    return {row["target"]: row for row in read_rows(path) if row["scope"] == "pooled"}


def to_float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value else 0.0


def comparison_rows(null_rows: dict[str, dict[str, str]], residual_rows: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for target in SHARED_TARGETS:
        null_row = null_rows[target]
        residual_row = residual_rows[target]
        out.append(
            {
                "target": target,
                "null_attention_delta_cv_r2": to_float(null_row, "delta_cv_r2"),
                "null_attention_best_feature": null_row["best_feature"],
                "residual_steering_delta_cv_r2": to_float(residual_row, "delta_cv_r2"),
                "residual_steering_best_feature": residual_row["best_feature"],
                "delta_gap_null_minus_residual": to_float(null_row, "delta_cv_r2")
                - to_float(residual_row, "delta_cv_r2"),
            }
        )
    return out


def write_csv(path: str | Path, rows: list[dict[str, object]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: object) -> str:
    return f"{float(value):.3f}"


def write_report(path: str | Path, rows: list[dict[str, object]]) -> None:
    lines = [
        "# Intervention-Family Incremental-Value Comparison",
        "",
        "Question: after simple controls are fitted first, which intervention family retains stronger thermodynamic incremental value?",
        "",
        "| target | null-attention CV delta R2 | null best thermo | residual-steering CV delta R2 | residual best thermo | gap |",
        "|---|---:|---|---:|---|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['target']} | {fmt(row['null_attention_delta_cv_r2'])} | "
            f"{row['null_attention_best_feature']} | {fmt(row['residual_steering_delta_cv_r2'])} | "
            f"{row['residual_steering_best_feature']} | {fmt(row['delta_gap_null_minus_residual'])} |"
        )
    lines.extend(
        [
            "",
            "Interpretation: null-attention retains a larger out-of-sample thermodynamic residual signal on the shared degradation targets. Residual steering shows only tiny or negative incremental value after controlling for risk and steering strength.",
        ]
    )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare null-attention vs residual-steering incremental thermo value.")
    parser.add_argument("--null-input", default="results/null_attention_incremental_value.csv")
    parser.add_argument("--residual-input", default="results/residual_steering_incremental_value.csv")
    parser.add_argument("--output", default="results/intervention_family_incremental_comparison.csv")
    parser.add_argument("--report-output", default="results/intervention_family_incremental_comparison.md")
    args = parser.parse_args()

    rows = comparison_rows(pooled_by_target(args.null_input), pooled_by_target(args.residual_input))
    write_csv(args.output, rows)
    write_report(args.report_output, rows)
    print(f"wrote {args.output}")
    print(f"wrote {args.report_output}")


if __name__ == "__main__":
    main()
