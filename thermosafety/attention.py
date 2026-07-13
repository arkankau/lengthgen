from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class NullAttractorConfig:
    risk_threshold: float = 0.52
    eta_null: float = 4.0
    kappa: float = 18.0
    lambda_penalty: float = 0.15
    beta_base: float = 1.0
    beta_collapse: float = 2.5
    null_key_scale: float = 0.0
    null_key_mode: str = "mean_logit"
    null_value_scale: float = 0.0
    null_value_mode: str = "zero"
    semantic_attractor_strength: float = 1.0
    redirect_risk_threshold: float = 0.75
    intervention_mix: float = 1.0
    phi_mode: str = "uniform"
    phi_unsafe_gain: float = 4.0


@dataclass(frozen=True)
class AttentionResult:
    output: np.ndarray
    attention: np.ndarray
    logits: np.ndarray
    risk: float
    beta: float
    null_bias: float


def _softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    shifted = x - np.max(x, axis=axis, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=axis, keepdims=True)


def null_attractor_attention(
    q: np.ndarray,
    k: np.ndarray,
    v: np.ndarray,
    risk: float,
    config: NullAttractorConfig | None = None,
) -> AttentionResult:
    """Run toy null-attractor attention over a single sequence.

    The null slot is appended as the final key/value. Risk changes the energy
    landscape by adding a null bias and a mild non-null penalty.
    """
    cfg = config or NullAttractorConfig()
    if q.ndim != 2 or k.ndim != 2 or v.ndim != 2:
        raise ValueError("q, k, and v must be rank-2 arrays")
    if q.shape != k.shape or q.shape != v.shape:
        raise ValueError("q, k, and v must have matching shapes")

    seq_len, dim = q.shape
    null_key = np.zeros((1, dim), dtype=float) + cfg.null_key_scale
    null_value = np.zeros((1, dim), dtype=float) + cfg.null_value_scale
    k_ext = np.vstack([k, null_key])
    v_ext = np.vstack([v, null_value])

    base_logits = q @ k_ext.T / np.sqrt(dim)
    null_gate = 1.0 / (1.0 + np.exp(-cfg.kappa * (risk - cfg.risk_threshold)))
    null_bias = cfg.eta_null * null_gate
    beta = cfg.beta_base + (cfg.beta_collapse - cfg.beta_base) * null_gate

    penalty = np.zeros_like(base_logits)
    penalty[:, :-1] = cfg.lambda_penalty * risk
    bias = np.zeros_like(base_logits)
    bias[:, -1] = null_bias

    logits = beta * (base_logits - penalty + bias)
    attention = _softmax(logits, axis=-1)
    output = attention @ v_ext
    return AttentionResult(
        output=output,
        attention=attention,
        logits=logits,
        risk=float(risk),
        beta=float(beta),
        null_bias=float(null_bias),
    )
