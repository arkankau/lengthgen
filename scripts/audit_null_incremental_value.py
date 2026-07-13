from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_steering_thermo import mean, spearman  # noqa: E402
from audit_thermo_incremental_value import (  # noqa: E402
    loocv_predict,
    ols_predict,
    r2_score,
    write_csv,
)


SIMPLE_FEATURES = [
    "risk",
    "eta_null",
    "lambda_penalty",
    "intervention_mix",
    "layer_value",
    "semantic_mode",
    "barrier_mode",
]
THERMO_FEATURES = [
    "mean_m_null",
    "mean_entropy",
    "mean_psi",
    "mean_spectral_gap",
    "thermo_collapse",
]
TARGETS = [
    "benign_damage",
    "jailbreak_unsafe",
    "jailbreak_safe_refusal",
    "collapse_failure",
    "utility_loss",
    "coherence",
]


def read_csv(path: str | Path) -> list[dict[str, object]]:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        out: list[dict[str, object]] = []
        for row in csv.DictReader(f):
            converted: dict[str, object] = {}
            for key, value in row.items():
                if value == "":
                    converted[key] = value
                    continue
                try:
                    converted[key] = float(value)
                except ValueError:
                    converted[key] = value
            out.append(converted)
        return out


def to_float(row: dict[str, object], key: str) -> float:
    value = row.get(key, 0.0)
    if value in {"", None}:
        return 0.0
    return float(value)


def target_rows(rows: list[dict[str, object]], target: str) -> list[dict[str, object]]:
    if target == "benign_damage":
        return [row for row in rows if str(row["label"]) == "benign"]
    if target in {"jailbreak_unsafe", "jailbreak_safe_refusal"}:
        return [row for row in rows if str(row["label"]) == "jailbreak"]
    return rows


def matrix(rows: list[dict[str, object]], features: list[str]) -> np.ndarray:
    return np.array([[to_float(row, feature) for feature in features] for row in rows], dtype=float)


def vector(rows: list[dict[str, object]], target: str) -> np.ndarray:
    return np.array([to_float(row, target) for row in rows], dtype=float)


def best_residual_thermo(rows: list[dict[str, object]], residuals: np.ndarray) -> dict[str, object]:
    if len(rows) < 2 or float(np.max(residuals) - np.min(residuals)) <= 1e-12:
        return {"best_feature": "", "best_abs_spearman": "", "best_spearman": ""}
    best = {"best_feature": "", "best_abs_spearman": -1.0, "best_spearman": 0.0}
    residual_list = [float(value) for value in residuals]
    for feature in THERMO_FEATURES:
        scores = [to_float(row, feature) for row in rows]
        rho = spearman(scores, residual_list)
        if abs(rho) > float(best["best_abs_spearman"]):
            best = {"best_feature": feature, "best_abs_spearman": abs(rho), "best_spearman": rho}
    return best


def group_values(rows: list[dict[str, object]], key: str) -> list[str]:
    return sorted({str(row.get(key, "")) for row in rows})


def filtered_rows(rows: list[dict[str, object]], key: str, value: str) -> list[dict[str, object]]:
    return [row for row in rows if str(row.get(key, "")) == value]


def audit_scope(rows: list[dict[str, object]], scope: str, target: str) -> dict[str, object]:
    y = vector(rows, target)
    if len(rows) < 3 or float(np.max(y) - np.min(y)) <= 1e-12:
        return {
            "scope": scope,
            "target": target,
            "n": len(rows),
            "positive_or_mean_target": mean([float(value) for value in y]) if len(y) else 0.0,
            "simple_r2": "",
            "simple_plus_thermo_r2": "",
            "delta_r2": "",
            "simple_cv_r2": "",
            "simple_plus_thermo_cv_r2": "",
            "delta_cv_r2": "",
            "best_feature": "",
            "best_abs_spearman": "",
            "best_spearman": "",
        }
    simple_x = matrix(rows, SIMPLE_FEATURES)
    full_x = matrix(rows, SIMPLE_FEATURES + THERMO_FEATURES)
    simple_pred = ols_predict(simple_x, y)
    full_pred = ols_predict(full_x, y)
    simple_cv_pred = loocv_predict(simple_x, y)
    full_cv_pred = loocv_predict(full_x, y)
    simple_r2 = r2_score(y, simple_pred)
    full_r2 = r2_score(y, full_pred)
    simple_cv_r2 = r2_score(y, simple_cv_pred)
    full_cv_r2 = r2_score(y, full_cv_pred)
    best = best_residual_thermo(rows, y - simple_pred)
    return {
        "scope": scope,
        "target": target,
        "n": len(rows),
        "positive_or_mean_target": mean([float(value) for value in y]),
        "simple_r2": simple_r2,
        "simple_plus_thermo_r2": full_r2,
        "delta_r2": full_r2 - simple_r2,
        "simple_cv_r2": simple_cv_r2,
        "simple_plus_thermo_cv_r2": full_cv_r2,
        "delta_cv_r2": full_cv_r2 - simple_cv_r2,
        **best,
    }


def audit_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for target in TARGETS:
        selected = target_rows(rows, target)
        out.append(audit_scope(selected, "pooled", target))
        for source in group_values(selected, "source"):
            out.append(audit_scope(filtered_rows(selected, "source", source), f"source:{source}", target))
    return out


def format_float(value: object) -> str:
    if value == "":
        return ""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return ""
    return f"{float(value):.3f}"


def write_report(path: str | Path, rows: list[dict[str, object]]) -> None:
    lines = [
        "# Null-Attention Incremental-Value Audit",
        "",
        "This report asks whether null-attention thermodynamic observables add predictive value after simple controls are fitted first.",
        "CV R2 is leave-one-out ridge R2; train R2 is descriptive.",
        "",
        "| scope | target | n | target mean | train simple R2 | train +thermo R2 | train delta R2 | CV simple R2 | CV +thermo R2 | CV delta R2 | best residual thermo | residual abs Spearman | residual Spearman |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['scope']} | {row['target']} | {row['n']} | {format_float(row['positive_or_mean_target'])} | "
            f"{format_float(row['simple_r2'])} | {format_float(row['simple_plus_thermo_r2'])} | "
            f"{format_float(row['delta_r2'])} | {format_float(row['simple_cv_r2'])} | "
            f"{format_float(row['simple_plus_thermo_cv_r2'])} | {format_float(row['delta_cv_r2'])} | "
            f"{row['best_feature']} | {format_float(row['best_abs_spearman'])} | {format_float(row['best_spearman'])} |"
        )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit null-attention thermo incremental value beyond simple controls.")
    parser.add_argument("--input-detail", default="results/steering_thermo_audit_pooled_detail.csv")
    parser.add_argument("--output", default="results/null_attention_incremental_value.csv")
    parser.add_argument("--report-output", default="results/null_attention_incremental_value_report.md")
    args = parser.parse_args()

    rows = read_csv(args.input_detail)
    audit = audit_rows(rows)
    write_csv(args.output, audit)
    write_report(args.report_output, audit)
    print(f"read {len(rows)} null-attention rows from {args.input_detail}")
    print(f"wrote {args.output}")
    print(f"wrote {args.report_output}")


if __name__ == "__main__":
    main()
