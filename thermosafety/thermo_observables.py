"""Thermodynamic observables of NATURAL attention (no injected probe).

For each query i in a head, the softmax attention p_ij is a Boltzmann distribution over keys with
energy E_ij = -s_ij (the scaled logit) and beta folded into the model's own scaling. Because energy
appears only inside a variance, additive constants cancel and every observable is computable from the
post-softmax weights alone:

    surprisal        u_ij   = -log p_ij           (energy up to a per-query constant)
    mean energy      <E>_i  = sum_j p_ij u_ij     = H_i  (the entropy)
    specific heat    C_i    = Var_j(u_ij; p_ij)   = <u^2>_i - <u>_i^2   (variance of energy)

C is the statistical-mechanics specific heat (energy fluctuation). It is small when attention is
either sharply peaked (one key dominates) or uniform, and large when many keys are in genuine
competition -- the signature of a "critically poised" head. Averaging over heads and queries gives a
per-layer profile C_l.
"""
from __future__ import annotations

import numpy as np

EPS = 1e-12


def _per_query_stats(p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """p: (..., K) attention weights along the last axis. Returns (entropy, specific_heat) with the
    last axis reduced."""
    p = np.clip(p, EPS, 1.0)
    u = -np.log(p)                     # surprisal / energy (up to constant)
    mean_u = np.sum(p * u, axis=-1)    # = entropy H
    mean_u2 = np.sum(p * u * u, axis=-1)
    var_u = np.maximum(mean_u2 - mean_u * mean_u, 0.0)
    return mean_u, var_u


def layer_observables(attn_layer: np.ndarray) -> dict[str, float]:
    """attn_layer: (heads, q_len, k_len) post-softmax weights for one layer.

    Returns per-layer scalars averaged over heads and query positions."""
    entropy, spec_heat = _per_query_stats(attn_layer)  # each (heads, q_len)
    return {
        "entropy": float(np.mean(entropy)),
        "specific_heat": float(np.mean(spec_heat)),
        "mean_energy": float(np.mean(entropy)),  # <E> = H here; kept explicit for clarity
    }


def trace_profiles(attentions: list[np.ndarray]) -> dict[str, list[float]]:
    """Per-layer profiles over a full trace's list of attention arrays."""
    keys = ("entropy", "specific_heat")
    out: dict[str, list[float]] = {k: [] for k in keys}
    for layer in attentions:
        obs = layer_observables(layer)
        for k in keys:
            out[k].append(obs[k])
    return out


def bootstrap_ci(values: np.ndarray, n_boot: int = 1000, alpha: float = 0.05,
                 rng: np.random.Generator | None = None) -> tuple[float, float, float]:
    """Mean and (lo, hi) percentile bootstrap CI over the first axis (samples)."""
    rng = rng or np.random.default_rng(0)
    values = np.asarray(values, dtype=float)
    n = len(values)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    idx = rng.integers(0, n, size=(n_boot, n))
    boots = values[idx].mean(axis=1)
    lo = float(np.percentile(boots, 100 * alpha / 2))
    hi = float(np.percentile(boots, 100 * (1 - alpha / 2)))
    return float(values.mean()), lo, hi
