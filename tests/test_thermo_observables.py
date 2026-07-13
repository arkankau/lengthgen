from __future__ import annotations

import unittest

import numpy as np

from thermosafety.thermo_observables import (
    _per_query_stats,
    bootstrap_ci,
    layer_observables,
    trace_profiles,
)


class SpecificHeatTests(unittest.TestCase):
    def test_uniform_distribution_has_zero_specific_heat(self):
        # uniform -> all surprisals equal -> zero variance of energy
        p = np.full((1, 4), 0.25)
        _, var = _per_query_stats(p)
        self.assertAlmostEqual(float(var[0]), 0.0, places=6)

    def test_delta_distribution_has_zero_specific_heat(self):
        # one key ~1.0 -> negligible variance of energy
        p = np.array([[1.0 - 3e-12, 1e-12, 1e-12, 1e-12]])
        _, var = _per_query_stats(p)
        self.assertLess(float(var[0]), 1e-3)

    def test_intermediate_distribution_has_positive_specific_heat(self):
        # a mix of high- and low-probability keys -> real energy fluctuation
        p = np.array([[0.7, 0.2, 0.05, 0.05]])
        _, var = _per_query_stats(p)
        self.assertGreater(float(var[0]), 0.1)

    def test_uniform_entropy_matches_log_k(self):
        p = np.full((1, 8), 1.0 / 8)
        ent, _ = _per_query_stats(p)
        self.assertAlmostEqual(float(ent[0]), np.log(8), places=5)

    def test_layer_observables_shapes_and_keys(self):
        rng = np.random.default_rng(0)
        logits = rng.normal(size=(3, 5, 5))
        p = np.exp(logits) / np.exp(logits).sum(axis=-1, keepdims=True)
        obs = layer_observables(p)
        self.assertIn("specific_heat", obs)
        self.assertIn("entropy", obs)
        self.assertGreaterEqual(obs["specific_heat"], 0.0)

    def test_trace_profiles_length_matches_layers(self):
        rng = np.random.default_rng(1)
        attentions = []
        for _ in range(4):
            logits = rng.normal(size=(2, 4, 4))
            p = np.exp(logits) / np.exp(logits).sum(axis=-1, keepdims=True)
            attentions.append(p)
        prof = trace_profiles(attentions)
        self.assertEqual(len(prof["specific_heat"]), 4)
        self.assertEqual(len(prof["entropy"]), 4)


class BootstrapTests(unittest.TestCase):
    def test_ci_brackets_mean(self):
        rng = np.random.default_rng(0)
        vals = rng.normal(loc=5.0, scale=1.0, size=200)
        mean, lo, hi = bootstrap_ci(vals, n_boot=500, rng=rng)
        self.assertLess(lo, mean)
        self.assertLess(mean, hi)
        self.assertAlmostEqual(mean, 5.0, delta=0.3)

    def test_tight_data_gives_tight_ci(self):
        vals = np.full(100, 3.0)
        mean, lo, hi = bootstrap_ci(vals, n_boot=200)
        self.assertAlmostEqual(lo, 3.0, places=6)
        self.assertAlmostEqual(hi, 3.0, places=6)


if __name__ == "__main__":
    unittest.main()
