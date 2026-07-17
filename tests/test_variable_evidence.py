import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "colab"))

import length_gen_colab as G


class VariableEvidenceTests(unittest.TestCase):
    def test_marked_sum_generators_return_requested_arity(self):
        rng = np.random.default_rng(7)
        for name, arity in (("pairadd", 2), ("tripleadd", 3), ("quadadd", 4)):
            tokens, answer_start, sources = G.TASKS[name]["make"](rng, 6, 6)
            self.assertEqual(len(sources), arity)
            expected = sum(tokens[index] for index in sources) % 10
            self.assertEqual(tokens[answer_start], expected)

    def test_sample_batch_pads_source_sets_to_task_arity(self):
        cfg = G.Cfg(task="quadadd", vocab=17, pad=G.QUAD_PAD, batch=2)
        _, _, _, _, targets = G.sample_batch(np.random.default_rng(8), 2, 6, 8, cfg)
        self.assertEqual(tuple(targets.shape), (2, 4))


if __name__ == "__main__":
    unittest.main()
