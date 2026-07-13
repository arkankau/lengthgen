"""Numerically verify the null-attractor theory against thermosafety/attention.py.

Claims under test:
 (A) Closed form: for query i, m_null[i] = sigmoid( beta(R) * (Delta_i + eta*g_R + lambda*R) )
     with g_R = sigmoid(kappa*(R - R_c)), Delta_i = z_null,i - F_real,i,
     z_null,i = q_i . k_null / sqrt(d), and F_real,i = (1/beta) logsumexp_j(beta * z_j,i).
 (B) Susceptibility (reduced regime beta const, lambda=0): chi(R) = d m_null / d R
     = beta*eta * m(1-m) * kappa * g_R(1-g_R), matches finite differences.
 (C) Confound-as-theorem: with a constant null key (z_null independent of the real-logit
     level), a uniform shift of all real logits changes F_real and hence m_null at FIXED risk
     -- the layer-scale confound. Setting z_null to the mean real logit (the mean_logit fix)
     makes Delta invariant to that shift, so m_null is unchanged. Demonstrated numerically.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thermosafety.attention import NullAttractorConfig, null_attractor_attention


def expit(x):
    return 1.0 / (1.0 + np.exp(-x))


def logsumexp(a, axis=None):
    a = np.asarray(a, dtype=float)
    if axis is None:
        amax = np.max(a)
        return float(np.log(np.sum(np.exp(a - amax))) + amax)
    amax = np.max(a, axis=axis, keepdims=True)
    out = np.log(np.sum(np.exp(a - amax), axis=axis, keepdims=True)) + amax
    return np.squeeze(out, axis=axis)


def empirical_m_null(q, k, v, risk, cfg):
    res = null_attractor_attention(q, k, v, risk, cfg)
    return res.attention[:, -1]  # null column, per query


def theory_m_null(q, k, risk, cfg):
    seq, dim = q.shape
    null_key = np.zeros((1, dim)) + cfg.null_key_scale
    z_null = (q @ null_key.T).ravel() / np.sqrt(dim)  # (seq,)
    z_real = (q @ k.T) / np.sqrt(dim)  # (seq, seq)
    g_R = expit(cfg.kappa * (risk - cfg.risk_threshold))
    beta = cfg.beta_base + (cfg.beta_collapse - cfg.beta_base) * g_R
    eta = cfg.eta_null
    lam = cfg.lambda_penalty
    F_real = logsumexp(beta * z_real, axis=1) / beta  # (seq,)
    delta = z_null - F_real
    u = beta * (delta + eta * g_R + lam * risk)
    return expit(u)


def test_A_closed_form():
    rng = np.random.default_rng(0)
    max_err = 0.0
    for trial in range(200):
        seq = int(rng.integers(2, 8))
        dim = int(rng.integers(2, 12))
        q = rng.normal(size=(seq, dim))
        k = rng.normal(size=(seq, dim))
        v = rng.normal(size=(seq, dim))
        cfg = NullAttractorConfig(
            risk_threshold=float(rng.uniform(0.2, 0.8)),
            eta_null=float(rng.uniform(0.0, 6.0)),
            kappa=float(rng.uniform(2.0, 20.0)),
            lambda_penalty=float(rng.uniform(0.0, 0.5)),
            beta_base=float(rng.uniform(0.5, 1.5)),
            beta_collapse=float(rng.uniform(1.5, 3.0)),
            null_key_scale=float(rng.uniform(-0.5, 0.5)),
        )
        risk = float(rng.uniform(0.0, 1.0))
        emp = empirical_m_null(q, k, v, risk, cfg)
        thy = theory_m_null(q, k, risk, cfg)
        max_err = max(max_err, float(np.max(np.abs(emp - thy))))
    print(f"(A) closed-form max abs error over 200 random trials: {max_err:.2e}")
    assert max_err < 1e-9, "closed form does not match implementation"


def test_B_susceptibility():
    rng = np.random.default_rng(1)
    seq, dim = 6, 8
    q = rng.normal(size=(seq, dim))
    k = rng.normal(size=(seq, dim))
    v = rng.normal(size=(seq, dim))
    # reduced regime: constant beta, no penalty
    beta = 2.0
    cfg = NullAttractorConfig(
        risk_threshold=0.5, eta_null=4.0, kappa=12.0, lambda_penalty=0.0,
        beta_base=beta, beta_collapse=beta, null_key_scale=0.0,
    )
    risks = np.linspace(0.01, 0.99, 999)  # fine grid: finite-diff error should approach O(step)
    m_emp = np.array([empirical_m_null(q, k, v, float(r), cfg).mean() for r in risks])
    # analytic per-query chi averaged over queries
    def chi_analytic(r):
        g = expit(cfg.kappa * (r - cfg.risk_threshold))
        z_real = (q @ k.T) / np.sqrt(dim)
        F = logsumexp(beta * z_real, axis=1) / beta
        m = expit(beta * (-F + cfg.eta_null * g))  # z_null=0
        gp = cfg.kappa * g * (1.0 - g)
        return (beta * cfg.eta_null * m * (1.0 - m) * gp).mean()
    chi_an = np.array([chi_analytic(float(r)) for r in risks])
    chi_fd = np.gradient(m_emp, risks)
    # compare on interior (finite-diff edges are noisy)
    err = np.max(np.abs(chi_an[2:-2] - chi_fd[2:-2]))
    peak_an = risks[np.argmax(chi_an)]
    peak_fd = risks[np.argmax(chi_fd)]
    print(f"(B) susceptibility: max|analytic - finite-diff| (interior, fine grid) = {err:.2e}")
    print(f"(B) susceptibility peak: analytic R={peak_an:.3f}, finite-diff R={peak_fd:.3f}, "
          f"R_c={cfg.risk_threshold} (peak sits below R_c by the bare-gap shift)")
    assert err < 2e-3, "susceptibility formula deviates from finite differences"
    assert abs(peak_an - peak_fd) <= 0.005, "peak location mismatch"


def m_null_from_logits(z_real, z_null, risk, beta, eta, kappa, R_c, lam):
    """m_null = sigmoid(beta*(z_null - F_real + eta*g_R + lambda*R)), F_real = logsumexp(beta z)/beta."""
    g = expit(kappa * (risk - R_c))
    F = logsumexp(beta * z_real) / beta
    return float(expit(beta * (z_null - F + eta * g + lam * risk)))


def test_C_confound_theorem():
    """The confound is a theorem. With Delta = z_null - F_real, a uniform ADDITIVE shift of the
    real logits (a layer sitting at a different offset) moves F_real by exactly that shift.

     - Constant null logit (z_null fixed): Delta, hence m_null, moves with the shift -> confound.
     - mean_logit null (z_null = mean of the real logits): both mean and F_real move by the same
       additive constant, so Delta is EXACTLY invariant -> the fix removes the additive confound.
    """
    rng = np.random.default_rng(2)
    n = 12
    z = rng.normal(size=n)  # real logits for one query
    risk = 0.3  # below threshold: null mass here is baseline, not risk-driven
    beta, eta, kappa, R_c, lam = 1.0, 4.0, 12.0, 0.5, 0.0
    shifts = [-1.0, 0.0, 1.0, 2.0]

    const_vals = [m_null_from_logits(z + c, 0.0, risk, beta, eta, kappa, R_c, lam) for c in shifts]
    fix_vals = [m_null_from_logits(z + c, float((z + c).mean()), risk, beta, eta, kappa, R_c, lam) for c in shifts]
    const_spread = max(const_vals) - min(const_vals)
    fix_spread = max(fix_vals) - min(fix_vals)
    print(f"(C) additive logit shifts {shifts}:")
    print(f"    constant null logit  m_null = {[round(v, 4) for v in const_vals]}  spread={const_spread:.4f} (confound)")
    print(f"    mean_logit null      m_null = {[round(v, 4) for v in fix_vals]}  spread={fix_spread:.2e} (invariant)")
    assert const_spread > 0.05, "expected the constant-null-logit baseline to move with the logit offset"
    assert fix_spread < 1e-12, "mean_logit fix should make m_null exactly invariant to additive shift"


if __name__ == "__main__":
    test_A_closed_form()
    test_B_susceptibility()
    test_C_confound_theorem()
    print("\nAll theory checks passed.")
