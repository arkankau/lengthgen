from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import torch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "colab"))
import pretrained_utility_selection as selection  # noqa: E402


class PretrainedUtilitySelectionTests(unittest.TestCase):
    def test_source_max_terms_match_directional_derivative(self):
        rows = torch.tensor([[[0.2, 0.7, 0.1], [0.6, 0.1, 0.3]]])
        gradients = torch.tensor([[[4.0, 1.0, 2.0], [-1.0, 3.0, 0.0]]])
        sources = torch.tensor([0])

        transfer, utility_gap, predicted_gain = selection.source_max_terms(
            rows, gradients, sources
        )

        self.assertTrue(torch.allclose(transfer, torch.tensor([[0.5, 0.0]])))
        self.assertTrue(torch.allclose(utility_gap, torch.tensor([[3.0, 0.0]])))
        self.assertTrue(torch.allclose(predicted_gain, torch.tensor([[1.5, 0.0]])))

    def test_negative_utility_predicts_harm_despite_available_transfer(self):
        rows = torch.tensor([[[0.1, 0.8, 0.1]]])
        gradients = torch.tensor([[[0.0, 2.0, 0.0]]])
        transfer, utility_gap, predicted_gain = selection.source_max_terms(
            rows, gradients, torch.tensor([0])
        )
        self.assertAlmostEqual(float(transfer[0, 0]), 0.7, places=6)
        self.assertAlmostEqual(float(utility_gap[0, 0]), -2.0, places=6)
        self.assertAlmostEqual(float(predicted_gain[0, 0]), -1.4, places=6)

    def test_select_circuit_uses_top_k_sum_with_stable_ties(self):
        scores = np.asarray([
            [0.9, 0.0, 0.0],
            [0.5, 0.5, -1.0],
            [0.4, 0.4, 0.4],
        ])
        layer, heads = selection.select_circuit(scores, head_count=2)
        self.assertEqual(layer, 1)
        self.assertEqual(heads, [0, 1])

    def test_selector_difference_is_paired(self):
        mass = {
            "source_max": {"records": [{"margin": 2.0}, {"margin": 1.0}]},
            "distractor_control": {"records": [{"margin": 1.0}, {"margin": 1.0}]},
        }
        utility = {
            "source_max": {"records": [{"margin": 4.0}, {"margin": 3.0}]},
            "distractor_control": {"records": [{"margin": 1.0}, {"margin": 2.0}]},
        }
        result = selection.selector_difference(mass, utility, seed=9)
        self.assertAlmostEqual(result["mean_margin_difference"], 1.5)
        self.assertEqual(result["estimand"], "utility_gain_effect_minus_source_mass_effect")


if __name__ == "__main__":
    unittest.main()
