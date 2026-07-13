from __future__ import annotations

import unittest

from scripts.compare_incremental_value_reports import comparison_rows


class IncrementalValueComparisonTests(unittest.TestCase):
    def test_comparison_rows_computes_null_minus_residual_gap(self):
        null_rows = {
            "utility_loss": {"target": "utility_loss", "delta_cv_r2": "0.10", "best_feature": "mean_entropy"},
            "coherence": {"target": "coherence", "delta_cv_r2": "0.08", "best_feature": "thermo_collapse"},
            "collapse_failure": {"target": "collapse_failure", "delta_cv_r2": "0.03", "best_feature": "mean_m_null"},
        }
        residual_rows = {
            "utility_loss": {"target": "utility_loss", "delta_cv_r2": "0.01", "best_feature": "basin_margin"},
            "coherence": {"target": "coherence", "delta_cv_r2": "0.02", "best_feature": "basin_margin"},
            "collapse_failure": {"target": "collapse_failure", "delta_cv_r2": "-0.01", "best_feature": "basin_entropy"},
        }

        rows = comparison_rows(null_rows, residual_rows)

        self.assertEqual(rows[0]["target"], "utility_loss")
        self.assertAlmostEqual(float(rows[0]["delta_gap_null_minus_residual"]), 0.09)


if __name__ == "__main__":
    unittest.main()
