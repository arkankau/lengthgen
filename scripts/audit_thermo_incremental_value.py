from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Iterable

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_steering_thermo import mean, spearman  # noqa: E402
from evaluate_residual_steering_audit import read_csv, setting_groups, write_csv  # noqa: E402


SIMPLE_FEATURES = ["risk", "layer", "alpha", "gate", "steering_strength"]
THERMO_FEATURES = [
    "native_entropy",
    "native_specific_heat",
    "basin_margin",
    "basin_entropy",
    "steering_alignment",
]
TARGETS = [
    "utility_loss",
    "coherence",
    "repetition_collapse",
    "template_collapse",
    "semantic_drift",
    "degradation_score",
    "collapse_failure",
]


def intervention_rows(rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    return [row for row in rows if str(row.get("mode", "")) == "residual_steering"]


def to_float(row: dict[str, object], key: str) -> float:
    value = row.get(key, 0.0)
    if value in {"", None}:
        return 0.0
    return float(value)


def matrix(rows: list[dict[str, object]], features: list[str]) -> np.ndarray:
    if not rows:
        return np.zeros((0, len(features)), dtype=float)
    return np.array([[to_float(row, feature) for feature in features] for row in rows], dtype=float)


def vector(rows: list[dict[str, object]], target: str) -> np.ndarray:
    return np.array([to_float(row, target) for row in rows], dtype=float)


def standardized_design(x: np.ndarray) -> np.ndarray:
    if x.ndim != 2:
        raise ValueError("expected a 2D design matrix")
    if x.shape[0] == 0:
        return np.ones((0, 1), dtype=float)
    std = x.std(axis=0)
    keep = std > 1e-12
    if keep.any():
        centered = (x[:, keep] - x[:, keep].mean(axis=0)) / std[keep]
        return np.column_stack([np.ones(x.shape[0]), centered])
    return np.ones((x.shape[0], 1), dtype=float)


def standardize_train_test(train_x: np.ndarray, test_x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    train_std = train_x.std(axis=0)
    keep = train_std > 1e-12
    if not keep.any():
        return np.ones((train_x.shape[0], 1), dtype=float), np.ones((test_x.shape[0], 1), dtype=float)
    mean_x = train_x[:, keep].mean(axis=0)
    train_design = (train_x[:, keep] - mean_x) / train_std[keep]
    test_design = (test_x[:, keep] - mean_x) / train_std[keep]
    return (
        np.column_stack([np.ones(train_x.shape[0]), train_design]),
        np.column_stack([np.ones(test_x.shape[0]), test_design]),
    )


def ols_predict(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    if len(y) == 0:
        return np.array([], dtype=float)
    design = standardized_design(x)
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    return design @ coef


def ridge_train_predict(train_x: np.ndarray, train_y: np.ndarray, test_x: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    if len(train_y) == 0:
        return np.zeros(test_x.shape[0], dtype=float)
    if len(train_y) == 1:
        return np.full(test_x.shape[0], float(train_y[0]), dtype=float)
    train_design, test_design = standardize_train_test(train_x, test_x)
    penalty = np.eye(train_design.shape[1]) * float(alpha)
    penalty[0, 0] = 0.0
    lhs = train_design.T @ train_design + penalty
    rhs = train_design.T @ train_y
    try:
        coef = np.linalg.solve(lhs, rhs)
    except np.linalg.LinAlgError:
        coef, *_ = np.linalg.lstsq(lhs, rhs, rcond=None)
    return test_design @ coef


def loocv_predict(x: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    if len(y) < 2:
        return y.copy()
    preds = np.zeros_like(y, dtype=float)
    for idx in range(len(y)):
        train_mask = np.ones(len(y), dtype=bool)
        train_mask[idx] = False
        preds[idx] = ridge_train_predict(x[train_mask], y[train_mask], x[~train_mask], alpha=alpha)[0]
    return preds


def r2_score(y: np.ndarray, pred: np.ndarray) -> float:
    if len(y) < 2:
        return 0.0
    denom = float(np.sum((y - y.mean()) ** 2))
    if denom <= 1e-12:
        return 0.0
    return float(1.0 - (np.sum((y - pred) ** 2) / denom))


def residualize(rows: list[dict[str, object]], target: str, features: list[str]) -> np.ndarray:
    y = vector(rows, target)
    return y - ols_predict(matrix(rows, features), y)


def best_residual_thermo(rows: list[dict[str, object]], residuals: np.ndarray) -> dict[str, object]:
    if len(rows) < 2 or float(np.max(residuals) - np.min(residuals)) <= 1e-12:
        return {"best_feature": "", "best_abs_spearman": "", "best_spearman": ""}
    best = {"best_feature": "", "best_abs_spearman": -1.0, "best_spearman": 0.0}
    residual_list = [float(v) for v in residuals]
    for feature in THERMO_FEATURES:
        scores = [to_float(row, feature) for row in rows]
        rho = spearman(scores, residual_list)
        if abs(rho) > float(best["best_abs_spearman"]):
            best = {"best_feature": feature, "best_abs_spearman": abs(rho), "best_spearman": rho}
    return best


def pooled_incremental_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out = []
    for target in TARGETS:
        y = vector(rows, target)
        simple_pred = ols_predict(matrix(rows, SIMPLE_FEATURES), y)
        full_pred = ols_predict(matrix(rows, SIMPLE_FEATURES + THERMO_FEATURES), y)
        simple_cv_pred = loocv_predict(matrix(rows, SIMPLE_FEATURES), y)
        full_cv_pred = loocv_predict(matrix(rows, SIMPLE_FEATURES + THERMO_FEATURES), y)
        residuals = y - simple_pred
        best = best_residual_thermo(rows, residuals)
        simple_r2 = r2_score(y, simple_pred)
        full_r2 = r2_score(y, full_pred)
        simple_cv_r2 = r2_score(y, simple_cv_pred)
        full_cv_r2 = r2_score(y, full_cv_pred)
        out.append(
            {
                "scope": "pooled",
                "target": target,
                "n": len(rows),
                "mean_target": mean([float(v) for v in y]),
                "simple_r2": simple_r2,
                "simple_plus_thermo_r2": full_r2,
                "delta_r2": full_r2 - simple_r2,
                "simple_cv_r2": simple_cv_r2,
                "simple_plus_thermo_cv_r2": full_cv_r2,
                "delta_cv_r2": full_cv_r2 - simple_cv_r2,
                **best,
            }
        )
    return out


def within_setting_incremental_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out = []
    groups = [group for group in setting_groups(rows) if len(group) >= 3]
    for target in TARGETS:
        per_group = []
        for group in groups:
            y = vector(group, target)
            if float(np.max(y) - np.min(y)) <= 1e-12:
                continue
            simple_pred = ols_predict(matrix(group, SIMPLE_FEATURES), y)
            full_pred = ols_predict(matrix(group, SIMPLE_FEATURES + THERMO_FEATURES), y)
            simple_cv_pred = loocv_predict(matrix(group, SIMPLE_FEATURES), y)
            full_cv_pred = loocv_predict(matrix(group, SIMPLE_FEATURES + THERMO_FEATURES), y)
            residuals = y - simple_pred
            best = best_residual_thermo(group, residuals)
            if best["best_abs_spearman"] == "":
                continue
            simple_r2 = r2_score(y, simple_pred)
            full_r2 = r2_score(y, full_pred)
            per_group.append(
                {
                    "simple_r2": simple_r2,
                    "full_r2": full_r2,
                    "delta_r2": full_r2 - simple_r2,
                    "simple_cv_r2": r2_score(y, simple_cv_pred),
                    "full_cv_r2": r2_score(y, full_cv_pred),
                    "delta_cv_r2": r2_score(y, full_cv_pred) - r2_score(y, simple_cv_pred),
                    "abs_spearman": float(best["best_abs_spearman"]),
                    "spearman": float(best["best_spearman"]),
                    "feature": str(best["best_feature"]),
                }
            )
        out.append(
            {
                "scope": "within_setting_mean",
                "target": target,
                "n": sum(len(group) for group in groups),
                "mean_target": mean([to_float(row, target) for row in rows]),
                "simple_r2": mean([row["simple_r2"] for row in per_group]) if per_group else "",
                "simple_plus_thermo_r2": mean([row["full_r2"] for row in per_group]) if per_group else "",
                "delta_r2": mean([row["delta_r2"] for row in per_group]) if per_group else "",
                "simple_cv_r2": mean([row["simple_cv_r2"] for row in per_group]) if per_group else "",
                "simple_plus_thermo_cv_r2": mean([row["full_cv_r2"] for row in per_group]) if per_group else "",
                "delta_cv_r2": mean([row["delta_cv_r2"] for row in per_group]) if per_group else "",
                "best_feature": most_common([row["feature"] for row in per_group]),
                "best_abs_spearman": mean([row["abs_spearman"] for row in per_group]) if per_group else "",
                "best_spearman": mean([row["spearman"] for row in per_group]) if per_group else "",
            }
        )
    return out


def most_common(values: list[str]) -> str:
    counts: dict[str, int] = {}
    for value in values:
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    if not counts:
        return ""
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def format_float(value: object) -> str:
    if value == "":
        return ""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return ""
    return f"{float(value):.3f}"


def write_report(path: str | Path, rows: list[dict[str, object]]) -> None:
    lines = [
        "# Thermodynamic Incremental-Value Audit",
        "",
        "This report asks whether thermodynamic features explain residual degradation after simple controls are fitted first.",
        "Train R2 is descriptive; CV R2 is the leave-one-out ridge estimate to reduce overfitting.",
        "",
        "| scope | target | n | train simple R2 | train +thermo R2 | train delta R2 | CV simple R2 | CV +thermo R2 | CV delta R2 | best residual thermo | residual abs Spearman | residual Spearman |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['scope']} | {row['target']} | {row['n']} | "
            f"{format_float(row['simple_r2'])} | {format_float(row['simple_plus_thermo_r2'])} | "
            f"{format_float(row['delta_r2'])} | {format_float(row['simple_cv_r2'])} | "
            f"{format_float(row['simple_plus_thermo_cv_r2'])} | {format_float(row['delta_cv_r2'])} | "
            f"{row['best_feature']} | "
            f"{format_float(row['best_abs_spearman'])} | {format_float(row['best_spearman'])} |"
        )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit thermo's incremental value beyond simple steering controls.")
    parser.add_argument("--input-detail", default="results/residual_steering_audit_expanded_detail.csv")
    parser.add_argument("--output", default="results/residual_steering_incremental_value.csv")
    parser.add_argument("--report-output", default="results/residual_steering_incremental_value_report.md")
    args = parser.parse_args()

    rows = intervention_rows(read_csv(args.input_detail))
    audit = pooled_incremental_rows(rows) + within_setting_incremental_rows(rows)
    write_csv(args.output, audit)
    write_report(args.report_output, audit)
    print(f"read {len(rows)} residual-steering rows from {args.input_detail}")
    print(f"wrote {args.output}")
    print(f"wrote {args.report_output}")


if __name__ == "__main__":
    main()
