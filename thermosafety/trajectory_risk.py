from __future__ import annotations

from dataclasses import dataclass

from thermosafety.real_model import RealModelTrace, hidden_state_features
from thermosafety.risk import score_risk


@dataclass(frozen=True)
class TrajectoryRiskBreakdown:
    score: float
    surface_score: float
    hidden_drift_score: float
    layer_path_score: float
    attention_concentration_score: float
    probe_score: float = 0.0


def _saturating(value: float, scale: float) -> float:
    if scale <= 0:
        raise ValueError("scale must be positive")
    return max(0.0, min(1.0, value / scale))


def score_trajectory_risk(
    trace: RealModelTrace,
    mode: str = "mixed",
    probe_score: float | None = None,
) -> TrajectoryRiskBreakdown:
    """Probe-style risk proxy over real-model trajectory features.

    This is still an interpretable hand-built probe. Its purpose is to move the
    control variable away from pure keywords and toward hidden-state dynamics.
    """
    features = hidden_state_features(trace)
    surface = score_risk(trace.prompt).score
    hidden_drift = _saturating(features["hidden_token_drift"], scale=12.0)
    layer_path = _saturating(features["layer_path_length"], scale=24.0)
    attention_concentration = max(
        0.0,
        min(1.0, features["native_attention_peak"]),
    )

    if mode == "surface":
        score = surface
    elif mode == "trajectory":
        score = 0.45 * hidden_drift + 0.35 * layer_path + 0.20 * attention_concentration
    elif mode == "mixed":
        score = (
            0.45 * surface
            + 0.25 * hidden_drift
            + 0.20 * layer_path
            + 0.10 * attention_concentration
        )
    elif mode == "probe":
        if probe_score is None:
            raise ValueError("probe mode requires probe_score")
        score = probe_score
    else:
        raise ValueError("mode must be one of: surface, trajectory, mixed, probe")

    return TrajectoryRiskBreakdown(
        score=max(0.0, min(1.0, score)),
        surface_score=surface,
        hidden_drift_score=hidden_drift,
        layer_path_score=layer_path,
        attention_concentration_score=attention_concentration,
        probe_score=0.0 if probe_score is None else probe_score,
    )
