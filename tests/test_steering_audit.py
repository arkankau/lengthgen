from __future__ import annotations

import unittest

from scripts.audit_steering_thermo import enrich_rows, rankdata, setting_summary, spearman, text_failure_features


class SteeringAuditTests(unittest.TestCase):
    def test_rankdata_averages_ties(self):
        self.assertEqual(rankdata([3.0, 1.0, 1.0]), [3.0, 1.5, 1.5])

    def test_spearman_detects_monotonic_relation(self):
        self.assertAlmostEqual(spearman([1.0, 2.0, 3.0], [10.0, 20.0, 30.0]), 1.0)
        self.assertAlmostEqual(spearman([1.0, 2.0, 3.0], [30.0, 20.0, 10.0]), -1.0)

    def test_text_failure_features_detect_loop(self):
        row = {
            "continuation_text": "Good Good Good Good Good Good Good Good",
            "continuation_chars": "39",
            "empty_continuation": "0.0",
        }
        baseline = {
            "continuation_text": "Photosynthesis converts light energy into chemical energy.",
            "continuation_chars": "55",
        }
        feats = text_failure_features(row, baseline)
        self.assertEqual(feats["collapse_failure"], 1.0)
        self.assertGreater(feats["utility_loss"], 0.0)

    def test_setting_summary_keeps_sources_separate(self):
        rows = [
            {
                "id": "x",
                "mode": "baseline",
                "continuation_text": "clear useful answer",
                "continuation_chars": "18",
            },
            {
                "id": "x",
                "mode": "null_intervention",
                "setting_id": "s001",
                "suite": "benign",
                "label": "benign",
                "risk": "0.1",
                "mean_m_null": "0.2",
                "mean_entropy": "1.0",
                "mean_psi": "0.1",
                "mean_spectral_gap": "0.5",
                "eta_null": "4.0",
                "lambda_penalty": "0.0",
                "intervention_mix": "1.0",
                "layers": "10",
                "null_value_mode": "zero",
                "phi_mode": "uniform",
                "continuation_text": "Good Good Good Good",
                "continuation_chars": "19",
                "empty_continuation": "0.0",
            },
        ]
        combined = enrich_rows(rows, source="a.csv") + enrich_rows(rows, source="b.csv")
        summary = setting_summary(combined)

        self.assertEqual(len(summary), 2)
        self.assertEqual({row["source"] for row in summary}, {"a.csv", "b.csv"})


if __name__ == "__main__":
    unittest.main()
