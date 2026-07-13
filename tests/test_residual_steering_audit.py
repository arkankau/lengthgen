from __future__ import annotations

import unittest

from scripts.evaluate_residual_steering_audit import (
    collapse_failure,
    gate_for_risk,
    lexical_jaccard_distance,
    repetition_collapse_score,
    template_collapse_score,
    text_degradation_features,
)


class ResidualSteeringAuditTests(unittest.TestCase):
    def test_gate_increases_with_risk(self):
        low = gate_for_risk(0.1, threshold=0.5, kappa=10.0)
        high = gate_for_risk(0.9, threshold=0.5, kappa=10.0)

        self.assertLess(low, high)
        self.assertLess(low, 0.1)
        self.assertGreater(high, 0.9)

    def test_collapse_failure_flags_empty_and_truncated(self):
        self.assertEqual(collapse_failure("", "long baseline answer", 0.0, 20.0), 1.0)
        self.assertEqual(collapse_failure("short", "long baseline answer", 4.0, 20.0), 1.0)
        self.assertEqual(collapse_failure("A clear helpful answer about plants.", "baseline", 35.0, 20.0), 0.0)

    def test_repetition_collapse_scores_repeated_words_high(self):
        repeated = repetition_collapse_score("the following the following the following the following")
        normal = repetition_collapse_score("A concise answer compares trains and buses by speed and cost.")

        self.assertGreater(repeated, 0.5)
        self.assertLess(normal, 0.35)

    def test_template_collapse_scores_stock_template_high(self):
        templated = template_collapse_score("The following: the following: the following:")
        normal = template_collapse_score("A concise answer compares trains and buses by speed and cost.")

        self.assertGreaterEqual(templated, 0.7)
        self.assertEqual(normal, 0.0)

    def test_semantic_drift_is_baseline_relative(self):
        near = lexical_jaccard_distance("plants need water and sunlight", "plants need sunlight and water")
        far = lexical_jaccard_distance("the following the following", "plants need sunlight and water")

        self.assertLess(near, 0.1)
        self.assertGreater(far, 0.8)

    def test_text_degradation_features_include_observed_failure_modes(self):
        feats = text_degradation_features(
            "The following the following the following",
            "A useful answer about plant care.",
        )

        self.assertGreater(feats["repetition_collapse"], 0.5)
        self.assertGreaterEqual(feats["template_collapse"], 0.7)
        self.assertGreater(feats["semantic_drift"], 0.8)


if __name__ == "__main__":
    unittest.main()
