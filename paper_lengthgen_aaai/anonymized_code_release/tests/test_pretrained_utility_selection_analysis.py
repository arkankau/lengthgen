from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze_pretrained_utility_selection as analysis  # noqa: E402


def condition(margins, correct):
    return {
        "records": [
            {"margin": margin, "correct": float(is_correct)}
            for margin, is_correct in zip(margins, correct)
        ]
    }


def fake_result(seed, utility_gain, mass_gain, baseline_accuracy=1.0):
    if baseline_accuracy == 1.0:
        correct = [1, 1]
    elif baseline_accuracy == 0.5:
        correct = [1, 0]
    else:
        correct = [0, 0]
    utility_conditions = {
        "baseline": condition([0.0, 0.0], correct),
        "distractor_control": condition([0.0, 0.0], correct),
        "source_max": condition(utility_gain, correct),
        "source_min": condition([-1.0, -1.0], correct),
    }
    mass_conditions = {
        "baseline": condition([0.0, 0.0], correct),
        "distractor_control": condition([0.0, 0.0], correct),
        "source_max": condition(mass_gain, correct),
        "source_min": condition([-0.5, -0.5], correct),
    }
    return {
        "seed": seed,
        "selectors": {
            "source_mass": {
                "selected_layer": 1,
                "selected_heads": [0],
                "lengths": {"5": {"conditions": mass_conditions}},
            },
            "utility_gain": {
                "selected_layer": 2,
                "selected_heads": [1],
                "lengths": {"5": {"conditions": utility_conditions}},
            },
        },
    }


class UtilitySelectionAnalysisTests(unittest.TestCase):
    def test_hierarchical_interval_resamples_seed_clusters(self):
        groups = [[1.0, 1.0], [3.0, 3.0]]
        interval = analysis.hierarchical_interval(groups, seed=4, draws=2000)
        self.assertLessEqual(interval[0], 1.1)
        self.assertGreaterEqual(interval[1], 2.9)

    def test_primary_gate_uses_competence_and_paired_selector_gain(self):
        results = [
            fake_result(seed, [2.0, 2.0], [0.0, 0.0])
            for seed in range(3)
        ]
        summary = analysis.aggregate(results, expected_lengths=(5,))
        row = summary["pooled_lengths"]["5"]
        self.assertTrue(summary["primary_gate_pass"])
        self.assertEqual(summary["confirmatory_lengths"], [5])
        self.assertAlmostEqual(
            row["utility_minus_source_mass_margin_effect"]["mean"], 2.0
        )

    def test_incompetent_length_is_diagnostic_not_confirmatory(self):
        results = [
            fake_result(seed, [2.0, 2.0], [0.0, 0.0], baseline_accuracy=0.0)
            for seed in range(3)
        ]
        summary = analysis.aggregate(results, expected_lengths=(5,))
        self.assertFalse(summary["pooled_lengths"]["5"]["competence_gate"])
        self.assertFalse(summary["primary_gate_pass"])


if __name__ == "__main__":
    unittest.main()
