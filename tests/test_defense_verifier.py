from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


@unittest.skipUnless(importlib.util.find_spec("torch"), "verifier imports optional deps")
class CoherenceHeuristicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from defense_verifier import coherence
        cls.coherence = staticmethod(coherence)

    def test_fluent_benign_scores_high(self):
        text = "Photosynthesis is a process by which plants convert light energy into chemical energy."
        self.assertGreater(self.coherence(text), 0.7)

    def test_repetition_loop_scores_low(self):
        text = "Good. Good. Good. Good. Good. Good. Good. Good. Good. Good."
        self.assertLess(self.coherence(text), 0.5)

    def test_run_together_text_scores_low(self):
        text = "CollegeorUniversityoruniversityofahighschoolusuallyanumbereroundoclass"
        self.assertLess(self.coherence(text), 0.6)

    def test_empty_scores_zero(self):
        self.assertEqual(self.coherence("   "), 0.0)

    def test_fluent_beats_degenerate(self):
        good = self.coherence("The main tradeoffs between trains and buses are cost and speed.")
        loop = self.coherence("Yes Yes Yes Yes Yes Yes Yes Yes Yes Yes")
        runon = self.coherence("GoodCityYourResponseThankYouVeryMuchIndeed")
        self.assertGreater(good, loop)
        self.assertGreater(good, runon)


if __name__ == "__main__":
    unittest.main()
