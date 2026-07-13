from __future__ import annotations

import unittest

import numpy as np

from thermosafety.attention import NullAttractorConfig, null_attractor_attention


def _expit(x):
    return 1.0 / (1.0 + np.exp(-x))


def _logsumexp_rows(a):
    amax = np.max(a, axis=1, keepdims=True)
    return (np.log(np.sum(np.exp(a - amax), axis=1, keepdims=True)) + amax).ravel()


def _logsumexp(a):
    amax = np.max(a)
    return float(np.log(np.sum(np.exp(a - amax))) + amax)


def _theory_m_null(q, k, risk, cfg):
    seq, dim = q.shape
    null_key = np.zeros((1, dim)) + cfg.null_key_scale
    z_null = (q @ null_key.T).ravel() / np.sqrt(dim)
    z_real = (q @ k.T) / np.sqrt(dim)
    g_R = _expit(cfg.kappa * (risk - cfg.risk_threshold))
    beta = cfg.beta_base + (cfg.beta_collapse - cfg.beta_base) * g_R
    F_real = _logsumexp_rows(beta * z_real) / beta
    delta = z_null - F_real
    return _expit(beta * (delta + cfg.eta_null * g_R + cfg.lambda_penalty * risk))


class OrderParameterTheory(unittest.TestCase):
    def test_closed_form_matches_implementation(self):
        """m_null = sigmoid(beta*(Delta + eta*g_R + lambda*R)) exactly (two-level Boltzmann)."""
        rng = np.random.default_rng(0)
        max_err = 0.0
        for _ in range(100):
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
            emp = null_attractor_attention(q, k, v, risk, cfg).attention[:, -1]
            thy = _theory_m_null(q, k, risk, cfg)
            max_err = max(max_err, float(np.max(np.abs(emp - thy))))
        self.assertLess(max_err, 1e-9)


class SusceptibilityTheory(unittest.TestCase):
    def test_analytic_susceptibility_matches_finite_differences(self):
        rng = np.random.default_rng(1)
        seq, dim, beta = 6, 8, 2.0
        q = rng.normal(size=(seq, dim))
        k = rng.normal(size=(seq, dim))
        v = rng.normal(size=(seq, dim))
        cfg = NullAttractorConfig(
            risk_threshold=0.5, eta_null=4.0, kappa=12.0, lambda_penalty=0.0,
            beta_base=beta, beta_collapse=beta, null_key_scale=0.0,
        )
        risks = np.linspace(0.01, 0.99, 999)
        m_emp = np.array([null_attractor_attention(q, k, v, float(r), cfg).attention[:, -1].mean() for r in risks])

        def chi_analytic(r):
            g = _expit(cfg.kappa * (r - cfg.risk_threshold))
            z_real = (q @ k.T) / np.sqrt(dim)
            F = _logsumexp_rows(beta * z_real) / beta
            m = _expit(beta * (-F + cfg.eta_null * g))
            gp = cfg.kappa * g * (1.0 - g)
            return float((beta * cfg.eta_null * m * (1.0 - m) * gp).mean())

        chi_an = np.array([chi_analytic(float(r)) for r in risks])
        chi_fd = np.gradient(m_emp, risks)
        self.assertLess(float(np.max(np.abs(chi_an[2:-2] - chi_fd[2:-2]))), 2e-3)
        # Predicted feature: the observable's critical point sits below the nominal gate midpoint R_c.
        self.assertLess(risks[int(np.argmax(chi_an))], cfg.risk_threshold)


class ConfoundTheorem(unittest.TestCase):
    def test_mean_logit_null_is_invariant_to_additive_logit_shift(self):
        """Delta = z_null - F_real. A constant null logit makes m_null move with the layer's logit
        offset (the confound); a mean-logit null makes Delta -- hence m_null -- exactly invariant."""
        rng = np.random.default_rng(2)
        z = rng.normal(size=12)
        risk, beta, eta, kappa, R_c, lam = 0.3, 1.0, 4.0, 12.0, 0.5, 0.0
        g = _expit(kappa * (risk - R_c))

        def m_null(z_real, z_null):
            F = _logsumexp(beta * z_real) / beta
            return float(_expit(beta * (z_null - F + eta * g + lam * risk)))

        shifts = [-1.0, 0.0, 1.0, 2.0]
        const = [m_null(z + c, 0.0) for c in shifts]
        fixed = [m_null(z + c, float((z + c).mean())) for c in shifts]
        self.assertGreater(max(const) - min(const), 0.05)
        self.assertLess(max(fixed) - min(fixed), 1e-12)


if __name__ == "__main__":
    unittest.main()
