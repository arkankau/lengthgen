from __future__ import annotations

import sys
import unittest
from pathlib import Path

import torch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "colab"))
import pretrained_natural_qa as natural  # noqa: E402


class NaturalQATests(unittest.TestCase):
    def test_answer_boundary_target_capitalizes_only_lowercase_initial(self):
        self.assertEqual(natural.answer_boundary_target("three"), "Three")
        self.assertEqual(natural.answer_boundary_target("Paris"), "Paris")
        self.assertEqual(natural.answer_boundary_target("  1998 "), "1998")

    def test_sentence_window_preserves_answer_offset(self):
        context = "First sentence. The capital is Paris. Last sentence."
        start = context.index("Paris")
        sentence, local = natural.sentence_containing(context, start, "Paris")
        self.assertEqual(sentence[local:local + 5], "Paris")
        self.assertIn("capital", sentence)

    def test_assemble_prompt_tracks_gold_answer_character(self):
        passages = ["Wrong fact.", "The capital is Paris.", "Other fact."]
        local = passages[1].index("Paris")
        prompt, source = natural.assemble_prompt(
            "What is the capital?", passages, 1, local
        )
        self.assertEqual(prompt[source:source + 5], "Paris")
        self.assertTrue(prompt.endswith("Answer:"))

    def test_collate_left_pads_and_shifts_source(self):
        short = natural.routing.Batch(
            tokens=torch.tensor([[4, 5]]),
            sources=torch.tensor([1]),
            answers=torch.tensor([9]),
        )
        long = natural.routing.Batch(
            tokens=torch.tensor([[6, 7, 8]]),
            sources=torch.tensor([0]),
            answers=torch.tensor([10]),
        )
        packed = natural.collate_batches([short, long], 0, 2, "cpu")[0]
        self.assertEqual(packed.tokens.tolist(), [[0, 4, 5], [6, 7, 8]])
        self.assertEqual(packed.attention_mask.tolist(), [[0, 1, 1], [1, 1, 1]])
        self.assertEqual(packed.sources.tolist(), [2, 0])


if __name__ == "__main__":
    unittest.main()
