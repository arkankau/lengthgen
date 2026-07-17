from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze_pretrained_causal_routing as analysis  # noqa: E402


class PretrainedCausalAnalysisTests(unittest.TestCase):
    def test_recovers_paired_intervals_from_saved_records(self):
        baseline = {
            "records": [
                {"correct": 0.0, "margin": -1.0},
                {"correct": 0.0, "margin": -0.5},
                {"correct": 1.0, "margin": 0.5},
            ]
        }
        intervention = {
            "records": [
                {"correct": 1.0, "margin": 0.5},
                {"correct": 1.0, "margin": 0.5},
                {"correct": 1.0, "margin": 1.0},
            ]
        }
        intervals = analysis.recover_intervals(baseline, intervention, 0, 5)
        self.assertGreaterEqual(intervals["accuracy_delta_ci95"][0], 0.0)
        self.assertGreater(intervals["margin_delta_ci95"][0], 0.0)

    def test_paired_intervals_compare_two_interventions(self):
        control = {
            "records": [
                {"correct": 0.0, "margin": -1.0},
                {"correct": 0.0, "margin": -0.5},
                {"correct": 0.0, "margin": -0.25},
            ]
        }
        source_max = {
            "records": [
                {"correct": 1.0, "margin": 0.5},
                {"correct": 1.0, "margin": 0.5},
                {"correct": 1.0, "margin": 0.25},
            ]
        }
        intervals = analysis.recover_intervals(control, source_max, 3, 20)
        self.assertGreater(intervals["accuracy_delta_ci95"][0], 0.0)
        self.assertGreater(intervals["margin_delta_ci95"][0], 0.0)


if __name__ == "__main__":
    unittest.main()
