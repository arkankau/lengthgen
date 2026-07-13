from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


def _normalize(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-12:
        return vector
    return vector / norm


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    a_norm = float(np.linalg.norm(a))
    b_norm = float(np.linalg.norm(b))
    if a_norm <= 1e-12 or b_norm <= 1e-12:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))


def energy_to_anchor(h: np.ndarray, anchor: np.ndarray) -> float:
    """E_b(X) = -cos(h(X), c_b). Lower energy means stronger basin alignment."""
    return -cosine(h, anchor)


@dataclass(frozen=True)
class BasinCentroids:
    """Single-anchor centroid per basin, e.g. {"safe": v, "unsafe": v, "benign": v}."""

    anchors: dict[str, np.ndarray] = field(default_factory=dict)

    def basins(self) -> list[str]:
        return sorted(self.anchors)


def basin_energies(h: np.ndarray, centroids: BasinCentroids) -> dict[str, float]:
    return {basin: energy_to_anchor(h, anchor) for basin, anchor in centroids.anchors.items()}


def boltzmann_occupancy(energies: dict[str, float], temperature: float = 1.0) -> dict[str, float]:
    """P(b) proportional to exp(-E_b / T), i.e. lower energy basins are favored."""
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    basins = sorted(energies)
    values = np.array([-energies[b] / temperature for b in basins], dtype=float)
    shifted = values - values.max()
    weights = np.exp(shifted)
    total = weights.sum()
    probs = weights / total if total > 0 else np.ones_like(weights) / len(weights)
    return {basin: float(prob) for basin, prob in zip(basins, probs)}


def basin_entropy(occupancy: dict[str, float]) -> float:
    probs = np.clip(np.array(list(occupancy.values()), dtype=float), 1e-12, 1.0)
    return float(-np.sum(probs * np.log(probs)))


def free_energy(energies: dict[str, float], temperature: float = 1.0) -> float:
    """F = -T * log(sum_b exp(-E_b / T)), the system free energy over basins."""
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    values = np.array([-e / temperature for e in energies.values()], dtype=float)
    shifted_max = values.max()
    log_sum = shifted_max + np.log(np.sum(np.exp(values - shifted_max)))
    return float(-temperature * log_sum)


def competition_margin(energies: dict[str, float], safe_key: str = "safe", unsafe_key: str = "unsafe") -> float:
    """Delta_E = E_unsafe - E_safe. Positive means the safe basin is energetically favored."""
    return float(energies[unsafe_key] - energies[safe_key])


def basin_selectivity(margins: list[float], labels: list[bool]) -> float:
    """sep(Delta_E) = mean(Delta_E | jailbreak) - mean(Delta_E | benign).

    `labels` is True for jailbreak-labeled cases, False for benign-labeled cases.
    """
    jailbreak_values = [m for m, is_jailbreak in zip(margins, labels) if is_jailbreak]
    benign_values = [m for m, is_jailbreak in zip(margins, labels) if not is_jailbreak]
    if not jailbreak_values or not benign_values:
        return 0.0
    return float(np.mean(jailbreak_values) - np.mean(benign_values))


def mean_anchor(vectors: list[np.ndarray]) -> np.ndarray:
    if not vectors:
        raise ValueError("mean_anchor requires at least one vector")
    return _normalize(np.mean(np.stack(vectors, axis=0), axis=0))


def build_refusal_subspace(diff_vectors: list[np.ndarray], k: int = 2) -> np.ndarray:
    """Top-k orthonormal directions spanning several refusal-minus-unsafe difference vectors.

    This tests whether the refusal/unsafe axis is well-approximated by a single
    mean-difference direction (the current `semantic_refusal` implementation)
    or whether it needs more than one dimension, per the refusal-cone finding
    in the literature (Wollschlager et al., ICML 2025).
    """
    if not diff_vectors:
        raise ValueError("build_refusal_subspace requires at least one vector")
    matrix = np.stack([_normalize(v) for v in diff_vectors], axis=0)
    k = min(k, matrix.shape[0], matrix.shape[1])
    _, _, vt = np.linalg.svd(matrix, full_matrices=False)
    return vt[:k]


def subspace_alignment(h: np.ndarray, basis: np.ndarray) -> float:
    """Generalized cosine: ||proj_basis(h)|| / ||h||, for an orthonormal `basis` (k, dim)."""
    h_norm = float(np.linalg.norm(h))
    if h_norm <= 1e-12:
        return 0.0
    projection = basis @ h
    return float(np.linalg.norm(projection) / h_norm)


def subspace_energy(h: np.ndarray, basis: np.ndarray) -> float:
    """Subspace analogue of `energy_to_anchor`: -subspace_alignment(h, basis)."""
    return -subspace_alignment(h, basis)


def orient_basis(basis: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Flip each basis row so it points toward `reference` (e.g. mean safe-minus-unsafe).

    SVD/PCA directions have arbitrary sign, so a raw top singular vector cannot be
    compared as a signed "safe vs unsafe" margin until oriented against a known
    reference direction.
    """
    oriented = basis.copy()
    for i in range(oriented.shape[0]):
        if np.dot(oriented[i], reference) < 0:
            oriented[i] = -oriented[i]
    return oriented


def signed_axis_projection(h: np.ndarray, direction: np.ndarray) -> float:
    """Signed cosine of `h` onto a single oriented direction (comparable to a safe/unsafe margin)."""
    return cosine(h, direction)


def residual_subspace_coupling(h: np.ndarray, basis: np.ndarray) -> float:
    """Alignment of `h` with subspace dimensions beyond the primary (first) direction.

    Nonzero residual coupling that also separates classes indicates the refusal/unsafe
    axis is not fully captured by one direction -- i.e. evidence for a refusal cone
    rather than a single refusal vector.
    """
    if basis.shape[0] <= 1:
        return 0.0
    return subspace_alignment(h, basis[1:])
