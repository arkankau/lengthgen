"""Depth-wise time-reversal irreversibility of the transformer residual stream.

The residual stream is a single shared vector space that every layer reads from and writes to,
so a token's hidden states h_0, h_1, ..., h_L form a trajectory in one common space with DEPTH as
the "time" axis. Porting the temporal-irreversibility idea from neuroscience (compare forward vs
time-reversed statistics), we measure irreversibility at each depth transition as the ANTISYMMETRIC
part of the lagged cross-covariance:

    K_l[i,j] = Cov( h_l[i], h_{l+1}[j] )        (over an ensemble of tokens)
    A_l      = K_l - K_l^T                       (antisymmetric part)
    irr_l    = ||A_l||_F^2 / (||K_l||_F^2 + eps) (scale-free: fraction of coupling that is antisymmetric)

For a time-reversible (detailed-balance) Gaussian process the lagged cross-covariance is symmetric,
so A_l = 0. A nonzero, depth-structured irr_l profile is a nonequilibrium "arrow of time across
depth". This is training-free and closed-form.
"""
from __future__ import annotations

import numpy as np

EPS = 1e-12


def common_pca_basis(H_all: np.ndarray, k: int) -> np.ndarray:
    """H_all: (n_samples, d) stacked hidden states across all depths/tokens. Returns (k, d) basis."""
    mu = H_all.mean(axis=0, keepdims=True)
    Xc = H_all - mu
    # economy SVD; right singular vectors are the principal axes
    _, _, vt = np.linalg.svd(Xc, full_matrices=False)
    k = min(k, vt.shape[0])
    return vt[:k]


def antisymmetric_fraction(X: np.ndarray, Y: np.ndarray) -> float:
    """Antisymmetric fraction of the cross-covariance between paired sets X (n,k) and Y (n,k)."""
    Xc = X - X.mean(axis=0, keepdims=True)
    Yc = Y - Y.mean(axis=0, keepdims=True)
    K = (Xc.T @ Yc) / max(1, X.shape[0])
    A = K - K.T
    num = float(np.sum(A * A))
    den = float(np.sum(K * K))
    return num / (den + EPS)


def raw_antisymmetric_norm(X: np.ndarray, Y: np.ndarray) -> float:
    Xc = X - X.mean(axis=0, keepdims=True)
    Yc = Y - Y.mean(axis=0, keepdims=True)
    K = (Xc.T @ Yc) / max(1, X.shape[0])
    A = K - K.T
    return float(np.sum(A * A))


def depth_irreversibility_profile(traj: np.ndarray, k: int = 20,
                                  basis: np.ndarray | None = None) -> dict[str, np.ndarray]:
    """traj: (n_tokens, n_layers, d) residual-stream trajectories.

    If `basis` (k, d) is given it is used directly (fit once, reuse across bootstrap/shuffle);
    otherwise a common PCA basis is fit on this data. Returns per-transition irreversibility
    (fraction and raw), plus the representation-change magnitude profile (for the redundancy check).
    """
    n, L, d = traj.shape
    if basis is None:
        basis = common_pca_basis(traj.reshape(n * L, d), k)  # (k, d)
    proj = traj @ basis.T  # (n, L, k)
    frac = np.zeros(L - 1)
    raw = np.zeros(L - 1)
    dh = np.zeros(L - 1)
    for l in range(L - 1):
        X = proj[:, l, :]
        Y = proj[:, l + 1, :]
        frac[l] = antisymmetric_fraction(X, Y)
        raw[l] = raw_antisymmetric_norm(X, Y)
        dh[l] = float(np.mean(np.linalg.norm(Y - X, axis=1)))
    return {"irr_fraction": frac, "irr_raw": raw, "repr_change": dh}


def shuffle_null_profile(traj: np.ndarray, k: int = 20, n_shuffles: int = 20,
                         rng: np.random.Generator | None = None,
                         basis: np.ndarray | None = None) -> np.ndarray:
    """Null: permute the DEPTH order per trajectory, destroying the true arrow, and measure the
    resulting irreversibility fraction. Returns (n_shuffles, L-1) null fractions. If the real
    profile is not above this null, there is no depth-ordered arrow of time."""
    rng = rng or np.random.default_rng(0)
    n, L, d = traj.shape
    out = np.zeros((n_shuffles, L - 1))
    for s in range(n_shuffles):
        perm = rng.permutation(L)
        shuffled = traj[:, perm, :]
        out[s] = depth_irreversibility_profile(shuffled, k=k, basis=basis)["irr_fraction"]
    return out


def bootstrap_profile(traj: np.ndarray, k: int = 20, n_boot: int = 200, alpha: float = 0.05,
                      rng: np.random.Generator | None = None,
                      basis: np.ndarray | None = None) -> dict[str, np.ndarray]:
    """Bootstrap CI over tokens for the irreversibility-fraction profile."""
    rng = rng or np.random.default_rng(0)
    n, L, d = traj.shape
    boots = np.zeros((n_boot, L - 1))
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boots[b] = depth_irreversibility_profile(traj[idx], k=k, basis=basis)["irr_fraction"]
    return {
        "mean": boots.mean(axis=0),
        "lo": np.percentile(boots, 100 * alpha / 2, axis=0),
        "hi": np.percentile(boots, 100 * (1 - alpha / 2), axis=0),
    }
