import sys
import json
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "colab"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import pretrained_natural_mcqa_ladder as ladder
from analyze_pretrained_natural_mcqa_ladder import aggregate


class NaturalMCQALadderTests(unittest.TestCase):
    def test_nested_passages_only_append_and_hold_gold_slot(self):
        nested = ladder.nested_passages("gold", [f"d{i}" for i in range(31)], 2, [4, 8, 16, 32])
        self.assertEqual(nested[4][2], "gold")
        self.assertEqual(nested[8][:4], nested[4])
        self.assertEqual(nested[16][:8], nested[8])
        self.assertEqual(nested[32][:16], nested[16])

    def test_passage_snippet_bounds_distractor_words(self):
        text = " ".join(f"word{i}" for i in range(30)) + ". A second sentence."
        self.assertEqual(len(ladder.passage_snippet(text).split()), 16)
        self.assertTrue(ladder.passage_snippet(text).startswith("word0 word1"))

    def test_atomic_checkpoint_replaces_complete_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            ladder.write_json_atomic(path, {"lengths": {"4": {"done": True}}})
            self.assertEqual(json.loads(path.read_text())["lengths"]["4"]["done"], True)
            self.assertFalse(Path(f"{path}.tmp").exists())

    def test_aggregate_recognizes_preregistered_direction(self):
        def condition(source, margin, correct, invariant=0.0):
            return {
                "records": [
                    {"source_mass": source, "margin": margin, "correct": correct},
                    {"source_mass": source, "margin": margin, "correct": correct},
                ],
                "invariant_max_abs_error": {
                    "sorted_weights": invariant,
                    "entropy": invariant / 2,
                },
            }

        rows = []
        for seed in (0, 1):
            lengths = {}
            for count, source, margin in ((4, .8, .8), (8, .6, .6), (16, .4, .4), (32, .2, .2)):
                lengths[str(count)] = {"conditions": {
                    "baseline": condition(source, margin, 1.0),
                    "source_max": condition(source, margin + .5, 1.0),
                    "matched_distractor_control": condition(source, margin, 1.0),
                }}
            rows.append({
                "model": "test/model",
                "seed": seed,
                "passage_counts": [4, 8, 16, 32],
                "pilot": {"gate_pass": True},
                "example_ids": {"calibration": list(range(64)), "evaluation": list(range(128))},
                "lengths": lengths,
            })
        summary = aggregate(rows, expected_seeds=(0, 1))
        self.assertTrue(summary["preregistered_success"])
        self.assertLess(summary["longest_minus_shortest"]["baseline_source_mass"]["mean"], 0)
        self.assertAlmostEqual(summary["invariant_max_abs_error"], 0.0)
        self.assertAlmostEqual(
            summary["trajectory"]["32"]["control_minus_baseline_margin"]["mean"], 0.0
        )

    def test_aggregate_reads_actual_invariant_diagnostic_keys(self):
        condition = {
            "records": [{"source_mass": 0.5, "margin": 0.5, "correct": 1.0}],
            "invariant_max_abs_error": {"sorted_weights": 2e-4, "entropy": 1e-5},
        }
        row = {
            "model": "test/model",
            "seed": 0,
            "passage_counts": [4],
            "pilot": {"gate_pass": True},
            "example_ids": {"calibration": [0], "evaluation": [0]},
            "lengths": {"4": {"conditions": {
                "baseline": condition,
                "source_max": condition,
                "matched_distractor_control": condition,
            }}},
        }
        summary = aggregate([row], expected_seeds=(0,))
        self.assertAlmostEqual(summary["invariant_max_abs_error"], 2e-4)

    def test_aggregate_rejects_mixed_model_pooling(self):
        rows = [
            {"model": "model/a", "seed": 0, "pilot": {"gate_pass": False}},
            {"model": "model/b", "seed": 0, "pilot": {"gate_pass": False}},
        ]
        with self.assertRaises(ValueError):
            aggregate(rows)


if __name__ == "__main__":
    unittest.main()
