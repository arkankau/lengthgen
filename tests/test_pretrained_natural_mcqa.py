import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "colab"))

import pretrained_natural_mcqa as mcqa


class NaturalMCQATests(unittest.TestCase):
    def test_prompt_contains_all_options_and_answer_boundary(self):
        prompt, source = mcqa.assemble_prompt(
            "Where?", ["Alpha is here."], ["Alpha", "Beta", "Gamma", "Delta"], 0, 0
        )
        self.assertEqual(source, prompt.index("Alpha is here."))
        self.assertTrue(prompt.endswith("Answer:"))
        for label in mcqa.LABELS:
            self.assertIn(f"{label}.", prompt)

    def test_no_context_prompt_has_no_passage(self):
        prompt, source = mcqa.assemble_prompt(
            "Where?", [], ["Alpha", "Beta", "Gamma", "Delta"]
        )
        self.assertIsNone(source)
        self.assertNotIn("Passage 1", prompt)

    def test_competence_filter_requires_context_and_gold_success(self):
        main = {"records": [{"correct": True}, {"correct": True}, {"correct": False}]}
        gold = {"records": [{"correct": True}, {"correct": False}, {"correct": True}]}
        no_context = {"records": [{"correct": False}, {"correct": False}, {"correct": False}]}
        self.assertEqual(mcqa.competence_indices(main, gold, no_context), [0])

    def test_generation_metrics_detect_repetition(self):
        fluent = mcqa.generation_text_metrics("A concise grounded answer")
        repeated = mcqa.generation_text_metrics("answer answer answer answer")
        self.assertEqual(fluent["repetition_fraction"], 0.0)
        self.assertGreater(repeated["repetition_fraction"], 0.7)


if __name__ == "__main__":
    unittest.main()
