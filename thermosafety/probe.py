from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from thermosafety.prompts import PromptCase
from thermosafety.real_model import RealModelTrace, hidden_state_features
from thermosafety.risk import score_risk


FEATURE_NAMES = [
    "surface_risk",
    "hidden_token_drift",
    "hidden_norm",
    "layer_path_length",
    "layer_step_mean",
    "layer_step_std",
    "layer_step_max",
    "early_layer_path",
    "late_layer_path",
    "late_to_early_path_ratio",
    "token_dispersion_final",
    "token_dispersion_delta",
    "first_last_drift_delta",
    "native_attention_entropy",
    "native_attention_peak",
    "last_first_cosine",
    "layer_displacement",
]

LATENT_FEATURE_NAMES = [
    name
    for name in FEATURE_NAMES
    if name != "surface_risk"
]


@dataclass(frozen=True)
class ProbeModel:
    feature_names: list[str]
    mean: np.ndarray
    scale: np.ndarray
    weights: np.ndarray
    bias: float
    l2: float
    epochs: int
    lr: float


def label_for_case(case: PromptCase) -> int:
    return int(case.label == "jailbreak" or "jailbreak" in case.suite)


def trace_feature_vector(
    case: PromptCase,
    trace: RealModelTrace,
    feature_names: list[str] | None = None,
) -> np.ndarray:
    features = hidden_state_features(trace)
    final = trace.hidden_states[-1]
    initial = trace.hidden_states[0]
    first = final[0]
    last = final[-1]
    denom = float(np.linalg.norm(first) * np.linalg.norm(last))
    last_first_cosine = float(np.dot(first, last) / denom) if denom else 0.0

    layer_centroids = np.vstack([layer.mean(axis=0) for layer in trace.hidden_states])
    layer_steps = np.linalg.norm(np.diff(layer_centroids, axis=0), axis=-1)
    midpoint = max(1, len(layer_steps) // 2)
    early_layer_path = float(np.sum(layer_steps[:midpoint])) if len(layer_steps) else 0.0
    late_layer_path = float(np.sum(layer_steps[midpoint:])) if len(layer_steps) else 0.0
    late_to_early_path_ratio = late_layer_path / (early_layer_path + 1e-8)

    first_layer = initial.mean(axis=0)
    last_layer = final.mean(axis=0)
    layer_displacement = float(np.linalg.norm(last_layer - first_layer))
    token_dispersion_initial = float(np.mean(np.linalg.norm(initial - initial.mean(axis=0), axis=-1)))
    token_dispersion_final = float(np.mean(np.linalg.norm(final - final.mean(axis=0), axis=-1)))
    initial_first_last_drift = float(np.linalg.norm(initial[-1] - initial[0]))
    final_first_last_drift = float(np.linalg.norm(final[-1] - final[0]))

    values = {
        "surface_risk": score_risk(case.prompt).score,
        "last_first_cosine": last_first_cosine,
        "layer_displacement": layer_displacement,
        "layer_step_mean": float(np.mean(layer_steps)) if len(layer_steps) else 0.0,
        "layer_step_std": float(np.std(layer_steps)) if len(layer_steps) else 0.0,
        "layer_step_max": float(np.max(layer_steps)) if len(layer_steps) else 0.0,
        "early_layer_path": early_layer_path,
        "late_layer_path": late_layer_path,
        "late_to_early_path_ratio": late_to_early_path_ratio,
        "token_dispersion_final": token_dispersion_final,
        "token_dispersion_delta": token_dispersion_final - token_dispersion_initial,
        "first_last_drift_delta": final_first_last_drift - initial_first_last_drift,
        **features,
    }
    names = FEATURE_NAMES if feature_names is None else feature_names
    return np.array([float(values[name]) for name in names], dtype=float)


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -40.0, 40.0)))


def fit_probe(
    x: np.ndarray,
    y: np.ndarray,
    feature_names: list[str] | None = None,
    l2: float = 0.05,
    epochs: int = 1200,
    lr: float = 0.08,
) -> ProbeModel:
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale = np.where(scale < 1e-8, 1.0, scale)
    z = (x - mean) / scale

    weights = np.zeros(z.shape[1], dtype=float)
    bias = 0.0
    n = max(1, len(y))
    for _ in range(epochs):
        pred = sigmoid(z @ weights + bias)
        error = pred - y
        grad_w = (z.T @ error) / n + l2 * weights
        grad_b = float(np.mean(error))
        weights -= lr * grad_w
        bias -= lr * grad_b

    return ProbeModel(
        feature_names=list(FEATURE_NAMES if feature_names is None else feature_names),
        mean=mean,
        scale=scale,
        weights=weights,
        bias=float(bias),
        l2=l2,
        epochs=epochs,
        lr=lr,
    )


def predict_probe(model: ProbeModel, x: np.ndarray) -> np.ndarray:
    z = (x - model.mean) / model.scale
    return sigmoid(z @ model.weights + model.bias)


def leave_one_out_predictions(
    x: np.ndarray,
    y: np.ndarray,
    feature_names: list[str] | None = None,
) -> np.ndarray:
    preds = np.zeros(len(y), dtype=float)
    for i in range(len(y)):
        mask = np.ones(len(y), dtype=bool)
        mask[i] = False
        model = fit_probe(x[mask], y[mask], feature_names=feature_names)
        preds[i] = predict_probe(model, x[i : i + 1])[0]
    return preds


def leave_group_out_predictions(
    x: np.ndarray,
    y: np.ndarray,
    groups: list[str],
    feature_names: list[str] | None = None,
) -> np.ndarray:
    preds = np.zeros(len(y), dtype=float)
    group_values = sorted(set(groups))
    for group in group_values:
        test_mask = np.array([value == group for value in groups], dtype=bool)
        train_mask = ~test_mask
        if len(set(y[train_mask].tolist())) < 2:
            preds[test_mask] = float(np.mean(y[train_mask])) if train_mask.any() else 0.0
            continue
        model = fit_probe(x[train_mask], y[train_mask], feature_names=feature_names)
        preds[test_mask] = predict_probe(model, x[test_mask])
    return preds
