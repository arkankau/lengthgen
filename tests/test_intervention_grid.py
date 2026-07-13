from __future__ import annotations

import unittest

from scripts.evaluate_intervention_grid import generation_features, parse_float_grid, parse_str_grid, summarize


class InterventionGridTests(unittest.TestCase):
    def test_generation_features_detect_empty_continuation(self):
        features = generation_features("hello world", "hello world")

        self.assertEqual(features["empty_continuation"], 1.0)
        self.assertEqual(features["continuation_chars"], 0.0)

    def test_parse_grids(self):
        self.assertEqual(parse_float_grid("1.0, 2.5"), [1.0, 2.5])
        self.assertEqual(parse_str_grid("4,5;all"), ["4,5", "all"])

    def test_summarize_groups_by_setting_mode_suite(self):
        rows = [
            {
                "setting_id": "s001",
                "mode": "null_intervention",
                "risk_source": "surface",
                "suite": "benign",
                "label": "benign",
                "layers": "4,5",
                "heads": "all",
                "risk_threshold": 0.2,
                "eta_null": 4.0,
                "kappa": 18.0,
                "beta_collapse": 2.5,
                "lambda_penalty": 0.0,
                "null_value_mode": "zero",
                "intervention_mix": 1.0,
                "semantic_attractor_strength": 1.0,
                "redirect_risk_threshold": 0.75,
                "phi_mode": "uniform",
                "risk": 0.1,
                "mean_m_null": 0.2,
                "mean_entropy": 1.0,
                "mean_psi": 0.1,
                "mean_spectral_gap": 0.5,
                "new_tokens": 4,
                "continuation_chars": 10,
                "unique_token_ratio": 1.0,
                "empty_continuation": 0.0,
                "length_delta_vs_baseline": -2,
            }
        ]
        summary = summarize(rows)

        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["suite"], "benign")
        self.assertAlmostEqual(summary[0]["mean_m_null"], 0.2)
        self.assertAlmostEqual(summary[0]["mean_entropy"], 1.0)


if __name__ == "__main__":
    unittest.main()
