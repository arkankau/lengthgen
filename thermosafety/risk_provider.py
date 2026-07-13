from __future__ import annotations

from typing import Any

import numpy as np

from thermosafety.probe import (
    FEATURE_NAMES,
    LATENT_FEATURE_NAMES,
    fit_probe,
    label_for_case,
    predict_probe,
    trace_feature_vector,
)
from thermosafety.prompts import PromptCase
from thermosafety.real_model import RealModelTrace, extract_trace_from_loaded
from thermosafety.risk import score_risk
from thermosafety.trajectory_risk import score_trajectory_risk


RISK_SOURCES = ("surface", "trajectory", "mixed", "probe_all", "probe_latent")


def _load_torch() -> Any:
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("latent risk sources require torch") from exc
    return torch


def _extract_traces_from_loaded(
    cases: list[PromptCase],
    tokenizer: Any,
    model: Any,
    device: str,
    max_length: int,
) -> list[tuple[PromptCase, RealModelTrace]]:
    torch = _load_torch()
    return [
        (
            case,
            extract_trace_from_loaded(
                prompt=case.prompt,
                torch=torch,
                tokenizer=tokenizer,
                model=model,
                max_length=max_length,
                device=device,
            ),
        )
        for case in cases
    ]


def risk_scores_for_cases(
    cases: list[PromptCase],
    source: str = "surface",
    tokenizer: Any | None = None,
    model: Any | None = None,
    device: str = "cpu",
    max_length: int = 128,
) -> dict[str, float]:
    """Compute the control variable R(X) for a batch of prompt cases.

    `surface` is the original transparent keyword heuristic. The other modes
    compute R(X) from hidden-state trajectories extracted from the loaded model.
    Probe modes fit a small calibration probe over the selected batch; validation
    scripts still use held-out predictions when estimating generalization.
    `probe_latent` intentionally excludes `surface_risk` from its feature vector.
    """
    if source not in RISK_SOURCES:
        raise ValueError(f"source must be one of: {', '.join(RISK_SOURCES)}")
    if source == "surface":
        return {case.id: score_risk(case.prompt).score for case in cases}

    if tokenizer is None or model is None:
        raise ValueError(f"{source} risk requires a loaded tokenizer and model")

    traces = _extract_traces_from_loaded(cases, tokenizer, model, device, max_length)
    if source in {"trajectory", "mixed"}:
        return {
            case.id: score_trajectory_risk(trace, mode=source).score
            for case, trace in traces
        }

    feature_names = FEATURE_NAMES if source == "probe_all" else LATENT_FEATURE_NAMES
    x = np.vstack([trace_feature_vector(case, trace, feature_names) for case, trace in traces])
    y = np.array([label_for_case(case) for case, _ in traces], dtype=float)
    if len(set(y.tolist())) < 2:
        fallback = float(np.mean(y)) if len(y) else 0.0
        return {case.id: fallback for case, _ in traces}

    probe = fit_probe(x, y, feature_names=feature_names)
    scores = predict_probe(probe, x)
    return {
        case.id: float(max(0.0, min(1.0, score)))
        for (case, _), score in zip(traces, scores)
    }
