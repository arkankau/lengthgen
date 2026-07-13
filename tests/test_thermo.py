from __future__ import annotations

import unittest

import numpy as np

from thermosafety.thermo import binned_means, max_finite_slope, risk_bins, summarize_transition


class ThermoTests(unittest.TestCase):
    def test_binned_means_counts_values(self):
        risks = np.array([0.0, 0.2, 0.8, 1.0])
        values = np.array([0.0, 0.2, 0.8, 1.0])
        edges = np.array([0.0, 0.5, 1.0])
        rows = binned_means(risks, values, edges)

        self.assertEqual(rows[0]["count"], 2.0)
        self.assertEqual(rows[1]["count"], 2.0)
        self.assertAlmostEqual(rows[1]["mean"], 0.9)

    def test_max_finite_slope_finds_transition(self):
        x = np.array([0.0, 0.4, 0.5, 1.0])
        y = np.array([0.0, 0.1, 0.9, 1.0])
        critical, slope = max_finite_slope(x, y)

        self.assertAlmostEqual(critical, 0.45)
        self.assertGreater(slope, 7.0)

    def test_summarize_transition_has_jump(self):
        rows = [
            {"risk": "0.0", "m_null": "0.0", "suite": "a"},
            {"risk": "0.2", "m_null": "0.1", "suite": "a"},
            {"risk": "0.8", "m_null": "0.9", "suite": "b"},
            {"risk": "1.0", "m_null": "1.0", "suite": "b"},
        ]
        summary = summarize_transition(rows, bins=4)

        self.assertGreater(summary.jump, 0.5)
        self.assertGreaterEqual(summary.universality_gap, 0.0)


if __name__ == "__main__":
    unittest.main()
