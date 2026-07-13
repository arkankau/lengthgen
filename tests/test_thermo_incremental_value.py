from __future__ import annotations

import unittest

import numpy as np

from scripts.audit_thermo_incremental_value import (
    loocv_predict,
    ols_predict,
    pooled_incremental_rows,
    r2_score,
    residualize,
)


class ThermoIncrementalValueTests(unittest.TestCase):
    def test_ols_predict_fits_linear_signal(self):
        x = np.array([[0.0], [1.0], [2.0], [3.0]])
        y = np.array([1.0, 3.0, 5.0, 7.0])

        pred = ols_predict(x, y)

        self.assertGreater(r2_score(y, pred), 0.999)

    def test_loocv_predict_returns_one_prediction_per_row(self):
        x = np.array([[0.0], [1.0], [2.0], [3.0], [4.0]])
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        pred = loocv_predict(x, y)

        self.assertEqual(pred.shape, y.shape)
        self.assertGreater(r2_score(y, pred), 0.5)

    def test_residualize_removes_simple_linear_control(self):
        rows = [
            {"risk": 0.0, "layer": 1.0, "alpha": 1.0, "gate": 0.0, "steering_strength": 0.0, "target": 1.0},
            {"risk": 1.0, "layer": 1.0, "alpha": 1.0, "gate": 1.0, "steering_strength": 1.0, "target": 3.0},
            {"risk": 2.0, "layer": 1.0, "alpha": 1.0, "gate": 2.0, "steering_strength": 2.0, "target": 5.0},
            {"risk": 3.0, "layer": 1.0, "alpha": 1.0, "gate": 3.0, "steering_strength": 3.0, "target": 7.0},
        ]

        residuals = residualize(rows, "target", ["risk", "layer", "alpha", "gate", "steering_strength"])

        self.assertLess(float(np.max(np.abs(residuals))), 1e-10)

    def test_pooled_incremental_rows_detects_extra_thermo_signal(self):
        rows = []
        for idx in range(12):
            risk = float(idx)
            thermo = 1.0 if idx % 2 else -1.0
            rows.append(
                {
                    "mode": "residual_steering",
                    "setting_id": "s001",
                    "risk": risk,
                    "layer": 1.0,
                    "alpha": 1.0,
                    "gate": risk,
                    "steering_strength": risk,
                    "native_entropy": thermo,
                    "native_specific_heat": 0.0,
                    "basin_margin": 0.0,
                    "basin_entropy": 0.0,
                    "steering_alignment": 0.0,
                    "utility_loss": risk + thermo,
                    "coherence": 1.0 - (0.01 * risk),
                    "repetition_collapse": 0.0,
                    "template_collapse": 0.0,
                    "semantic_drift": 0.0,
                    "degradation_score": risk + thermo,
                    "collapse_failure": float(idx > 8),
                }
            )

        audit = {row["target"]: row for row in pooled_incremental_rows(rows)}

        self.assertGreater(float(audit["utility_loss"]["delta_r2"]), 0.05)
        self.assertEqual(audit["utility_loss"]["best_feature"], "native_entropy")


if __name__ == "__main__":
    unittest.main()
