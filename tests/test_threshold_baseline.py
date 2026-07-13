from __future__ import annotations

import unittest

from scripts.compare_threshold_baseline import best_threshold, rates, threshold_predictions


class ThresholdBaselineTests(unittest.TestCase):
    def test_threshold_predictions_replace_order_parameter(self):
        rows = [
            {"risk": "0.1", "suite": "benign", "label": "benign"},
            {"risk": "0.9", "suite": "direct_jailbreak", "label": "jailbreak"},
        ]
        pred = threshold_predictions(rows, 0.5)

        self.assertEqual(pred[0]["m_null"], "0.0")
        self.assertEqual(pred[1]["m_null"], "1.0")

    def test_rates_compute_tpr_fpr(self):
        rows = [
            {"risk": "0.1", "suite": "benign", "label": "benign"},
            {"risk": "0.9", "suite": "direct_jailbreak", "label": "jailbreak"},
        ]
        pred = threshold_predictions(rows, 0.5)
        result = rates(pred)

        self.assertEqual(result["jailbreak_collapse_rate"], 1.0)
        self.assertEqual(result["benign_false_collapse_rate"], 0.0)

    def test_best_threshold_separates_simple_rows(self):
        rows = [
            {"risk": "0.1", "suite": "benign", "label": "benign"},
            {"risk": "0.9", "suite": "direct_jailbreak", "label": "jailbreak"},
        ]
        threshold = best_threshold(rows)

        self.assertGreater(threshold, 0.1)
        self.assertLess(threshold, 0.9)


if __name__ == "__main__":
    unittest.main()
