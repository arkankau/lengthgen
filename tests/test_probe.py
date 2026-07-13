from __future__ import annotations

import unittest

import numpy as np

from thermosafety.probe import fit_probe, leave_group_out_predictions, leave_one_out_predictions, predict_probe


class ProbeTests(unittest.TestCase):
    def test_probe_fits_separable_toy_data(self):
        x = np.array(
            [
                [0.0, 0.1],
                [0.1, 0.2],
                [1.0, 0.9],
                [0.9, 1.0],
            ],
            dtype=float,
        )
        y = np.array([0.0, 0.0, 1.0, 1.0], dtype=float)

        model = fit_probe(x, y, epochs=400)
        pred = predict_probe(model, x)
        self.assertLess(pred[:2].mean(), 0.5)
        self.assertGreater(pred[2:].mean(), 0.5)

    def test_leave_one_out_predictions_are_probabilities(self):
        x = np.array(
            [
                [0.0, 0.1],
                [0.1, 0.2],
                [1.0, 0.9],
                [0.9, 1.0],
            ],
            dtype=float,
        )
        y = np.array([0.0, 0.0, 1.0, 1.0], dtype=float)

        pred = leave_one_out_predictions(x, y)
        self.assertEqual(pred.shape, y.shape)
        self.assertTrue(np.all(pred >= 0.0))
        self.assertTrue(np.all(pred <= 1.0))

    def test_leave_group_out_predictions_are_probabilities(self):
        x = np.array(
            [
                [0.0, 0.1],
                [0.1, 0.2],
                [1.0, 0.9],
                [0.9, 1.0],
            ],
            dtype=float,
        )
        y = np.array([0.0, 0.0, 1.0, 1.0], dtype=float)
        groups = ["a", "a", "b", "b"]

        pred = leave_group_out_predictions(x, y, groups)
        self.assertEqual(pred.shape, y.shape)
        self.assertTrue(np.all(pred >= 0.0))
        self.assertTrue(np.all(pred <= 1.0))


if __name__ == "__main__":
    unittest.main()
