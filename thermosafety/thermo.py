from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TransitionSummary:
    critical_risk: float
    max_slope: float
    susceptibility_peak_risk: float
    susceptibility_peak: float
    low_risk_m_null: float
    high_risk_m_null: float
    jump: float
    universality_gap: float


def mean(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def risk_bins(risks: np.ndarray, bins: int = 8) -> np.ndarray:
    if bins < 2:
        raise ValueError("bins must be at least 2")
    lo = float(np.min(risks))
    hi = float(np.max(risks))
    if hi <= lo:
        hi = lo + 1e-6
    return np.linspace(lo, hi, bins + 1)


def binned_means(
    risks: np.ndarray,
    values: np.ndarray,
    edges: np.ndarray,
) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for i in range(len(edges) - 1):
        left = edges[i]
        right = edges[i + 1]
        if i == len(edges) - 2:
            mask = (risks >= left) & (risks <= right)
        else:
            mask = (risks >= left) & (risks < right)
        selected = values[mask]
        rows.append(
            {
                "bin_left": float(left),
                "bin_right": float(right),
                "bin_mid": float((left + right) / 2.0),
                "count": float(len(selected)),
                "mean": float(np.mean(selected)) if len(selected) else 0.0,
                "variance": float(np.var(selected)) if len(selected) else 0.0,
            }
        )
    return rows


def max_finite_slope(xs: np.ndarray, ys: np.ndarray) -> tuple[float, float]:
    order = np.argsort(xs)
    xs = xs[order]
    ys = ys[order]
    best_slope = 0.0
    best_x = float(xs[0]) if len(xs) else 0.0
    for i in range(1, len(xs)):
        dx = float(xs[i] - xs[i - 1])
        if abs(dx) < 1e-12:
            continue
        slope = float((ys[i] - ys[i - 1]) / dx)
        if abs(slope) > abs(best_slope):
            best_slope = slope
            best_x = float((xs[i] + xs[i - 1]) / 2.0)
    return best_x, best_slope


def universality_gap(
    rows: list[dict[str, str]],
    edges: np.ndarray,
    risk_key: str = "risk",
    value_key: str = "m_null",
    suite_key: str = "suite",
) -> float:
    risks = np.array([float(row[risk_key]) for row in rows], dtype=float)
    values = np.array([float(row[value_key]) for row in rows], dtype=float)
    global_bins = binned_means(risks, values, edges)
    gaps: list[float] = []
    suites = sorted({row[suite_key] for row in rows})
    for suite in suites:
        suite_rows = [row for row in rows if row[suite_key] == suite]
        suite_risks = np.array([float(row[risk_key]) for row in suite_rows], dtype=float)
        suite_values = np.array([float(row[value_key]) for row in suite_rows], dtype=float)
        suite_bins = binned_means(suite_risks, suite_values, edges)
        for global_bin, suite_bin in zip(global_bins, suite_bins):
            if suite_bin["count"] > 0 and global_bin["count"] > 0:
                gaps.append(abs(suite_bin["mean"] - global_bin["mean"]))
    return mean(gaps)


def summarize_transition(rows: list[dict[str, str]], bins: int = 8) -> TransitionSummary:
    risks = np.array([float(row["risk"]) for row in rows], dtype=float)
    m_null = np.array([float(row["m_null"]) for row in rows], dtype=float)
    edges = risk_bins(risks, bins=bins)
    m_bins = binned_means(risks, m_null, edges)
    mids = np.array([row["bin_mid"] for row in m_bins], dtype=float)
    means = np.array([row["mean"] for row in m_bins], dtype=float)
    variances = np.array([row["variance"] for row in m_bins], dtype=float)

    critical_risk, max_slope = max_finite_slope(mids, means)
    susceptibility_index = int(np.argmax(variances)) if len(variances) else 0
    low = mean([row["mean"] for row in m_bins[: max(1, bins // 4)]])
    high = mean([row["mean"] for row in m_bins[-max(1, bins // 4) :]])
    return TransitionSummary(
        critical_risk=critical_risk,
        max_slope=max_slope,
        susceptibility_peak_risk=float(mids[susceptibility_index]) if len(mids) else 0.0,
        susceptibility_peak=float(variances[susceptibility_index]) if len(variances) else 0.0,
        low_risk_m_null=low,
        high_risk_m_null=high,
        jump=high - low,
        universality_gap=universality_gap(rows, edges),
    )
