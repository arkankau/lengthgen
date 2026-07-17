from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import torch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "colab"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze_pretrained_critical as critical_analysis  # noqa: E402
import pretrained_causal_routing as routing  # noqa: E402
import pretrained_format_pilot as format_pilot  # noqa: E402
import pretrained_selection_robustness as selection  # noqa: E402
import pretrained_utility_gap as utility  # noqa: E402


class PretrainedUtilityGapTests(unittest.TestCase):
    def test_fixed_competitor_excludes_answer(self):
        logits = torch.tensor([[5.0, 4.0, 3.0], [2.0, 7.0, 6.0]])
        answers = torch.tensor([0, 1])
        self.assertTrue(torch.equal(utility.fixed_competitor(logits, answers), torch.tensor([1, 2])))

    def test_transfer_mass_uses_signed_swap_direction(self):
        rows = torch.tensor([[[0.2, 0.7, 0.1], [0.4, 0.3, 0.3]]])
        sources = torch.tensor([0])
        maximum = utility.transfer_mass(rows, sources, "source_max")
        minimum = utility.transfer_mass(rows, sources, "source_min")
        self.assertTrue(torch.allclose(maximum, torch.tensor([[0.5, 0.0]])))
        self.assertTrue(torch.allclose(minimum, torch.tensor([[-0.1, -0.1]])))

    def test_interpolation_gradient_is_permutation_direction(self):
        weights = torch.tensor([[[[0.1, 0.6, 0.3]]]], requires_grad=False)
        alpha = torch.zeros(1, 1, requires_grad=True)
        patched = routing.patch_attention_weights(
            weights, torch.tensor([0]), [0], "source_max_interp", {}, alpha
        )
        value = torch.tensor([1.0, -2.0, 0.5])
        objective = (patched[0, 0, -1] * value).sum()
        objective.backward()
        expected = (0.6 - 0.1) * (value[0] - value[1])
        self.assertAlmostEqual(float(alpha.grad[0, 0]), float(expected), places=6)

    def test_summary_reports_directional_agreement(self):
        records = [
            {
                "exact_margin_delta": 2.0,
                "first_order_margin_delta": 1.5,
                "utility_gap_by_head": [3.0, float("nan")],
            },
            {
                "exact_margin_delta": -1.0,
                "first_order_margin_delta": -0.5,
                "utility_gap_by_head": [-2.0, 1.0],
            },
        ]
        summary = utility.summarize(records, seed=5)
        self.assertEqual(summary["sign_agreement"], 1.0)
        self.assertAlmostEqual(summary["positive_utility_fraction"], 2 / 3)


class PretrainedSelectionRobustnessTests(unittest.TestCase):
    def test_selection_recomputes_best_layer_for_each_k(self):
        score = torch.tensor([
            [9.0, 8.0, 0.0, 0.0],
            [6.0, 6.0, 6.0, 6.0],
            [1.0, 1.0, 1.0, 1.0],
        ])
        self.assertEqual(selection.select_layer_heads(score, 2)[0], 0)
        self.assertEqual(selection.select_layer_heads(score, 4)[0], 1)

    def test_config_grid_contains_selected_and_layer_controls(self):
        score = np.arange(48, dtype=float).reshape(6, 8)
        configs = selection.config_grid(score, seed=2)
        names = {config["name"] for config in configs}
        self.assertTrue({"selected_k2", "selected_k4", "selected_k8"}.issubset(names))
        self.assertIn("random_layer", names)
        self.assertTrue(any(name.startswith("adjacent_") for name in names))

    def test_max_control_contrast_is_paired(self):
        conditions = {
            "source_max": {"records": [
                {"correct": 1.0, "margin": 2.0},
                {"correct": 1.0, "margin": 1.0},
            ]},
            "distractor_control": {"records": [
                {"correct": 0.0, "margin": 0.0},
                {"correct": 1.0, "margin": 0.5},
            ]},
        }
        result = selection.max_control_contrast(conditions, seed=4)
        self.assertEqual(result["accuracy_delta"], 0.5)
        self.assertEqual(result["margin_delta"], 1.25)
        self.assertGreater(result["margin_delta_ci95"][0], 0.0)


class PretrainedCriticalAnalysisTests(unittest.TestCase):
    def test_format_gate_requires_competence_direction_and_invariants(self):
        def condition(mode, accuracy, margins, correct=None):
            correct = correct or [1.0, 0.0]
            return {
                "mode": mode,
                "accuracy": accuracy,
                "records": [
                    {"correct": correct[index], "margin": margins[index]}
                    for index in range(2)
                ],
                "invariant_max_abs_error": {"sorted": 1e-7} if mode != "baseline" else {},
            }

        lengths = {}
        for length in (5, 20):
            lengths[str(length)] = {
                "conditions": {
                    "baseline": condition("baseline", 0.5, [0.0, 0.0]),
                    "source_max": condition("source_max", 1.0, [2.0, 1.0]),
                    "source_min": condition("source_min", 0.0, [-2.0, -1.0]),
                    "distractor_control": condition("distractor_control", 0.5, [0.0, 0.0]),
                },
                "contrasts_vs_baseline": [
                    {"mode": "source_max", "margin_delta": 1.5, "margin_delta_ci95": [1.0, 2.0]},
                    {"mode": "source_min", "margin_delta": -1.5, "margin_delta_ci95": [-2.0, -1.0]},
                    {"mode": "distractor_control", "margin_delta": 0.0, "margin_delta_ci95": [-0.1, 0.1]},
                ],
            }
        result = critical_analysis.summarize_format({
            "model": "test", "format": "equals_newline", "lengths": lengths
        })
        self.assertTrue(result["gate_pass"])

    def test_utility_aggregate_preserves_seed_level_replication(self):
        items = []
        for seed, correlation in enumerate((0.5, 0.7, 0.9)):
            items.append({
                "model": "test",
                "seed": seed,
                "rows": [
                    {
                        "mode": "source_max",
                        "spearman_first_order_exact": correlation,
                        "sign_agreement": 0.75,
                        "mean_exact_margin_delta": 1.0,
                    },
                    {
                        "mode": "source_max",
                        "spearman_first_order_exact": correlation - 0.1,
                        "sign_agreement": 0.80,
                        "mean_exact_margin_delta": 0.5,
                    },
                ],
            })
        result = critical_analysis.aggregate_utility(items)[0]
        self.assertTrue(result["gate_pass"])
        self.assertEqual(result["n_seeds"], 3)
        self.assertEqual(result["positive_source_max_cells"], 6)
        self.assertAlmostEqual(result["mean_seed_sign_agreement"], 0.775)

    def test_utility_aggregate_fails_when_registered_seeds_are_missing(self):
        item = {
            "model": "test",
            "seed": 0,
            "rows": [{
                "mode": "source_max",
                "spearman_first_order_exact": 0.8,
                "sign_agreement": 0.9,
                "mean_exact_margin_delta": 1.0,
            }],
        }
        result = critical_analysis.aggregate_utility([item], expected_seeds=(0, 1, 2))[0]
        self.assertFalse(result["gate_pass"])
        self.assertEqual(result["missing_seeds"], [1, 2])

    def test_llama_gate_records_negative_source_forcing(self):
        def condition(mode, accuracy, margins):
            return {
                "mode": mode,
                "accuracy": accuracy,
                "records": [
                    {"correct": float(margin > 0), "margin": margin}
                    for margin in margins
                ],
                "invariant_max_abs_error": {"sorted": 1e-7} if mode != "baseline" else {},
            }

        lengths = {}
        for length in (5, 20):
            lengths[str(length)] = {
                "conditions": {
                    "baseline": condition("baseline", 0.5, [1.0, -1.0]),
                    "source_max": condition("source_max", 0.5, [0.5, -1.5]),
                    "source_min": condition("source_min", 0.5, [0.0, -2.0]),
                    "distractor_control": condition("distractor_control", 0.5, [1.0, -1.0]),
                },
                "contrasts_vs_baseline": [
                    {"mode": "source_max", "margin_delta": -0.5, "margin_delta_ci95": [-1.0, 0.0]},
                    {"mode": "source_min", "margin_delta": -1.0, "margin_delta_ci95": [-1.5, -0.5]},
                    {"mode": "distractor_control", "margin_delta": 0.0, "margin_delta_ci95": [-0.1, 0.1]},
                ],
            }
        pilot = {"formats": {"colon_newline": {"5": {"accuracy": 0.5}}}}
        result = critical_analysis.summarize_llama_replication(
            pilot, {"model": "llama", "format": "colon_newline", "lengths": lengths}
        )
        self.assertFalse(result["gate_pass"])
        self.assertEqual(result["positive_max_control_cells"], 0)


class PretrainedFormatPilotTests(unittest.TestCase):
    def test_select_format_uses_gate_then_locked_tie_break(self):
        results = {
            "first": {
                "5": {"accuracy": 0.50},
                "20": {"accuracy": 0.30},
            },
            "second": {
                "5": {"accuracy": 0.45},
                "20": {"accuracy": 0.35},
            },
            "fails": {
                "5": {"accuracy": 0.90},
                "20": {"accuracy": 0.10},
            },
        }
        winner, eligible = format_pilot.select_format(
            results, ["first", "second", "fails"], [5, 20], 0.40, 0.25
        )
        self.assertEqual(winner, "second")
        self.assertEqual(eligible, ["first", "second"])

    def test_select_format_returns_none_when_gate_fails(self):
        results = {
            "candidate": {
                "5": {"accuracy": 0.39},
                "20": {"accuracy": 0.50},
            }
        }
        winner, eligible = format_pilot.select_format(
            results, ["candidate"], [5, 20], 0.40, 0.25
        )
        self.assertIsNone(winner)
        self.assertEqual(eligible, [])


if __name__ == "__main__":
    unittest.main()
