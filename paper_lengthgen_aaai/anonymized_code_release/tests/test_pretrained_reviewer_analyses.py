from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze_pretrained_dose_response as dose  # noqa: E402
import analyze_pretrained_natural_qa as natural  # noqa: E402
import analyze_pretrained_natural_mcqa as natural_mcqa  # noqa: E402
import analyze_pretrained_selector_ablation as selector  # noqa: E402


def records(values):
    return [{"margin": float(value), "correct": 1.0} for value in values]


class ReviewerAnalysisTests(unittest.TestCase):
    def test_natural_mcqa_requires_multi_token_generation_audit(self):
        results = []
        for seed in range(2):
            conditions = {
                "source_max": {"records": records([2.0, 2.0])},
                "matched_distractor_control": {"records": records([0.0, 0.0])},
            }
            generation = {
                "source_max": {"records": [
                    {"first_token_correct": 1.0, "repetition_fraction": 0.0},
                    {"first_token_correct": 1.0, "repetition_fraction": 0.0},
                ]},
                "matched_distractor_control": {"records": [
                    {"first_token_correct": 0.0, "repetition_fraction": 0.0},
                    {"first_token_correct": 0.0, "repetition_fraction": 0.0},
                ]},
            }
            results.append({
                "seed": seed,
                "pilot": {
                    "gate_pass": True,
                    "context_gain_is_conditional": True,
                    "main": {"accuracy": 1.0},
                    "gold_only": {"accuracy": 1.0},
                    "no_context": {"accuracy": 0.0},
                    "context_accuracy_gain": 1.0,
                },
                "selectors": {
                    "source_mass": {"conditions": conditions},
                    "utility_gain": {"conditions": conditions},
                },
                "free_generation": {"conditions": generation},
            })
        summary = natural_mcqa.aggregate(results)
        self.assertTrue(summary["stage1_replicated_success"])
        self.assertFalse(summary["preregistered_success"])
        self.assertIn("first_token_accuracy", summary["free_generation"])

    def test_selector_success_requires_utility_to_rank_first(self):
        results = []
        names = ["source_mass", "transfer_mass", "utility_gap", "utility_gain",
                 "source_gradient", "gradient_magnitude", "random"]
        for seed in range(3):
            rows = {}
            for name in names:
                gain = 2.0 if name == "utility_gain" else 0.0
                rows[name] = {
                    "source_max": {"records": records([gain, gain])},
                    "distractor_control": {"records": records([0.0, 0.0])},
                }
            results.append({"seed": seed, "selectors": rows})
        summary = selector.aggregate(results, expected_seeds=(0, 1, 2))
        self.assertTrue(summary["preregistered_success"])
        self.assertEqual(summary["ranking"][0], "utility_gain")

    def test_dose_response_checks_the_complete_path(self):
        results = []
        alphas = [0.0, 0.5, 1.0]
        for seed in range(3):
            rows = {}
            for alpha in alphas:
                rows[str(alpha)] = {
                    "source_max": {"records": records([alpha, alpha])},
                    "matched_control": {"records": records([0.0, 0.0])},
                }
            results.append({"seed": seed, "alphas": alphas, "dose_response": rows})
        summary = dose.aggregate(results, expected_seeds=(0, 1, 2))
        self.assertTrue(summary["preregistered_success"])
        self.assertTrue(summary["mean_effect_nondecreasing"])

    def test_natural_qa_needs_two_gate_passing_seeds(self):
        results = []
        for seed in range(3):
            gate = seed < 2
            selectors = {}
            if gate:
                selectors = {
                    "source_mass": {"conditions": {
                        "source_max": {"records": records([0.0, 0.0])},
                        "matched_distractor_control": {"records": records([0.0, 0.0])},
                    }},
                    "utility_gain": {"conditions": {
                        "source_max": {"records": records([2.0, 2.0])},
                        "matched_distractor_control": {"records": records([0.0, 0.0])},
                    }},
                }
            results.append({
                "seed": seed,
                "pilot": {
                    "gate_pass": gate,
                    "main": {"accuracy": 0.75 if gate else 0.25},
                    "gold_only": {"accuracy": 0.75},
                    "no_context": {"accuracy": 0.0},
                    "context_accuracy_gain": 0.75 if gate else 0.25,
                },
                "selectors": selectors,
            })
        summary = natural.aggregate(results)
        self.assertTrue(summary["preregistered_success"])
        self.assertTrue(summary["multi_evidence_triggered"])


if __name__ == "__main__":
    unittest.main()
