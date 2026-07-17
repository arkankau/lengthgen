from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "colab"))
import pretrained_selector_ablation as ablation  # noqa: E402


class SelectorAblationTests(unittest.TestCase):
    def test_build_selectors_uses_each_registered_score(self):
        matrix = [[0.0, 1.0], [2.0, 0.0]]
        calibration = {key: matrix for key in ablation.SCORE_KEYS.values()}
        selectors = ablation.build_selectors(calibration, head_count=1, seed=3)
        self.assertEqual(set(selectors), set(ablation.SCORE_KEYS) | {"random"})
        for name in ablation.SCORE_KEYS:
            self.assertEqual(selectors[name]["selected_layer"], 1)
            self.assertEqual(selectors[name]["selected_heads"], [0])

    def test_effect_records_is_paired(self):
        source_max = {"records": [{"margin": 3.0}, {"margin": 1.0}]}
        control = {"records": [{"margin": 1.0}, {"margin": 2.0}]}
        effect = ablation.effect_records(source_max, control)
        self.assertTrue(np.array_equal(effect, np.asarray([2.0, -1.0])))


if __name__ == "__main__":
    unittest.main()
