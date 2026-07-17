import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "colab"))

from competence_matched_arity_search import CANDIDATES, candidate_args


class CompetenceMatchedArityTests(unittest.TestCase):
    def test_candidate_order_increases_capacity(self):
        parameter_scales = [row["layers"] * row["width"] ** 2 for row in CANDIDATES]
        self.assertEqual(parameter_scales, sorted(parameter_scales))

    def test_candidate_args_preserves_output_configuration(self):
        base = SimpleNamespace(outdir="out", checkpoint_dir="checkpoints", warmup=800)
        merged = candidate_args(base, CANDIDATES[0])
        self.assertEqual(merged.outdir, "out")
        self.assertEqual(merged.layers, 4)
        self.assertLessEqual(merged.warmup, merged.steps // 10)


if __name__ == "__main__":
    unittest.main()
