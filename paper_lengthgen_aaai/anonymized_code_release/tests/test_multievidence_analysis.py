from __future__ import annotations

import unittest

from scripts.analyze_multievidence_routing import summarize


def result(seed, base, maximum, minimum, control):
    def condition(mode, exact, mass):
        return {
            "mode": mode,
            "exact_match": exact,
            "token_accuracy": exact,
            "selected_head_source_mass": mass,
            "invariant_max_abs_error": {} if mode == "baseline" else {"sorted": 0.0},
        }

    return {
        "cfg": {"task": "pairadd", "pe": "nope", "seed": seed},
        "train_length": {"exact_match": 1.0, "token_accuracy": 1.0},
        "lengths": {
            "25": {
                "conditions": {
                    "baseline": condition("baseline", base, 0.4),
                    "source_max": condition("source_max", maximum, 0.7),
                    "source_min": condition("source_min", minimum, 0.0),
                    "distractor_control": condition("distractor_control", control, 0.4),
                }
            }
        },
    }


class MultiEvidenceAnalysisTests(unittest.TestCase):
    def test_summary_keeps_assignment_contrast_separate_from_control(self):
        summary = summarize([
            result(0, 0.4, 0.6, 0.2, 0.4),
            result(1, 0.5, 0.7, 0.1, 0.5),
        ])
        row = summary["by_length"]["25"]
        self.assertTrue(summary["all_models_competent"])
        self.assertAlmostEqual(row["mean_source_max_exact_delta"], 0.2)
        self.assertAlmostEqual(row["mean_source_min_exact_delta"], -0.3)
        self.assertAlmostEqual(row["mean_distractor_control_exact_delta"], 0.0)
        self.assertAlmostEqual(row["mean_max_minus_min_exact"], 0.5)
        self.assertAlmostEqual(row["mean_max_minus_control_exact"], 0.2)
        self.assertEqual(summary["max_invariant_error"], 0.0)


if __name__ == "__main__":
    unittest.main()
