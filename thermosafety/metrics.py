from __future__ import annotations

import numpy as np


def null_mass(attention: np.ndarray) -> float:
    return float(np.mean(attention[:, -1]))


def attention_entropy(attention: np.ndarray) -> float:
    clipped = np.clip(attention, 1e-12, 1.0)
    return float(np.mean(-np.sum(clipped * np.log(clipped), axis=-1)))


def null_selective_psi(attention: np.ndarray) -> float:
    non_null = attention[:, :-1]
    return float(np.mean(attention[:, -1] - np.max(non_null, axis=-1)))


def spectral_gap(attention: np.ndarray) -> float:
    """Approximate absorbing-null spectral gap from the token-token kernel."""
    kernel = attention[:, :-1]
    row_sums = kernel.sum(axis=1, keepdims=True)
    normalized = np.divide(kernel, row_sums, out=np.zeros_like(kernel), where=row_sums > 0)
    if normalized.shape[0] == 1:
        return 1.0
    eigvals = np.linalg.eigvals(normalized)
    magnitudes = sorted((abs(v) for v in eigvals), reverse=True)
    lambda_2 = magnitudes[1] if len(magnitudes) > 1 else 0.0
    return float(max(0.0, 1.0 - lambda_2))
