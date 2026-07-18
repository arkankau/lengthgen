from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
from transformers.masking_utils import ALL_MASK_ATTENTION_FUNCTIONS, eager_mask


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "colab"))
import pretrained_causal_routing as routing  # noqa: E402


class PretrainedCausalRoutingTests(unittest.TestCase):
    def tearDown(self):
        routing.PATCH_STATE = None
        routing.EAGER_CAPTURE_LAYER = None
        routing.LAST_CAPTURED_ATTENTION = None

    def test_custom_backend_registers_eager_causal_mask(self):
        routing.register_attention_backend()
        self.assertIs(ALL_MASK_ATTENTION_FUNCTIONS["routing_eager"], eager_mask)

    def test_repeat_kv_matches_grouped_query_heads(self):
        states = torch.tensor([[[[1.0]], [[2.0]]]])
        repeated = routing.repeat_kv(states, 2)
        self.assertEqual(tuple(repeated.shape), (1, 4, 1, 1))
        self.assertTrue(torch.equal(repeated[:, :, 0, 0], torch.tensor([[1.0, 1.0, 2.0, 2.0]])))

    def test_formatted_example_preserves_unique_answer_source(self):
        rng = np.random.default_rng(7)
        tokens, source, answer = routing.build_formatted_example(
            list(range(100, 180)), 8, [11, 12], [13], rng
        )
        self.assertEqual(tokens[source], answer)
        self.assertEqual(tokens.count(answer), 1)

    def test_patch_preserves_spectrum_and_moves_only_selected_heads(self):
        weights = torch.rand(2, 3, 4, 4)
        weights = weights / weights.sum(dim=-1, keepdim=True)
        sources = torch.tensor([1, 2])
        diagnostics = {}
        patched = routing.patch_attention_weights(weights, sources, [0, 2], "source_max", diagnostics)
        self.assertTrue(torch.equal(weights.sort(dim=-1).values, patched.sort(dim=-1).values))
        self.assertEqual(diagnostics["sorted"], 0.0)
        for batch, source in enumerate(sources):
            for head in (0, 2):
                self.assertEqual(
                    patched[batch, head, -1, source],
                    weights[batch, head, -1].max(),
                )
            self.assertTrue(torch.equal(patched[batch, 1], weights[batch, 1]))

    def test_distractor_control_preserves_source_weight(self):
        weights = torch.rand(2, 2, 3, 3)
        weights = weights / weights.sum(dim=-1, keepdim=True)
        sources = torch.tensor([0, 1])
        patched = routing.patch_attention_weights(weights, sources, [0, 1], "distractor_control", {})
        for batch, source in enumerate(sources):
            self.assertTrue(torch.equal(weights[batch, :, -1, source], patched[batch, :, -1, source]))

    def test_patch_records_mean_displacement_for_each_example(self):
        weights = torch.tensor([
            [[[0.10, 0.60, 0.30]], [[0.20, 0.50, 0.30]]],
            [[[0.40, 0.10, 0.50]], [[0.25, 0.25, 0.50]]],
        ])
        diagnostics = {}
        routing.patch_attention_weights(
            weights, torch.tensor([0, 1]), [0, 1], "source_max", diagnostics
        )
        self.assertEqual(len(diagnostics["mean_l1_displacement_by_example"]), 2)
        self.assertAlmostEqual(diagnostics["mean_l1_displacement_by_example"][0], 0.8)
        self.assertAlmostEqual(diagnostics["mean_l1_displacement_by_example"][1], 0.65)

    def test_matched_distractor_control_preserves_source_and_spectrum(self):
        weights = torch.tensor([[[[0.10, 0.45, 0.30, 0.15]]]])
        sources = torch.tensor([0])
        patched = routing.patch_attention_weights(
            weights, sources, [0], "matched_distractor_control", {}
        )
        self.assertEqual(patched[0, 0, -1, 0], weights[0, 0, -1, 0])
        self.assertTrue(torch.equal(
            patched.sort(dim=-1).values, weights.sort(dim=-1).values
        ))

    def test_matched_pair_approximates_source_transfer(self):
        row = torch.tensor([0.10, 0.45, 0.30, 0.15])
        pair = routing.matched_distractor_pair(row, source=0, target_delta=torch.tensor(0.35))
        self.assertEqual(pair, (1, 3))

    def test_vectorized_matched_pair_matches_exhaustive_search(self):
        torch.manual_seed(11)
        row = torch.rand(17)
        source = 5
        target = torch.tensor(0.23)
        candidates = [index for index in range(row.numel()) if index != source]
        expected = min(
            (
                (abs(abs(float(row[left] - row[right])) - float(target)), left, right)
                for offset, left in enumerate(candidates)
                for right in candidates[offset + 1 :]
            ),
            key=lambda item: item[0],
        )[1:]
        self.assertEqual(routing.matched_distractor_pair(row, source, target), expected)

    def test_sorted_matched_pair_has_exhaustive_optimal_error(self):
        generator = torch.Generator().manual_seed(29)
        for length in range(3, 24):
            row = torch.rand(length, generator=generator)
            source = length // 3
            target = torch.rand((), generator=generator)
            candidates = [index for index in range(length) if index != source]
            expected_error = min(
                abs(abs(float(row[left] - row[right])) - float(target))
                for offset, left in enumerate(candidates)
                for right in candidates[offset + 1 :]
            )
            pair = routing.matched_distractor_pair(row, source, target)
            actual_error = abs(abs(float(row[pair[0]] - row[pair[1]])) - float(target))
            self.assertAlmostEqual(actual_error, expected_error, places=6)

    def test_interpolated_patch_has_natural_and_swapped_endpoints(self):
        weights = torch.tensor([[[[0.1, 0.6, 0.3]]]], dtype=torch.float32)
        sources = torch.tensor([0])
        natural = routing.patch_attention_weights(
            weights, sources, [0], "source_max_interp", {}, torch.zeros(1, 1)
        )
        swapped = routing.patch_attention_weights(
            weights, sources, [0], "source_max_interp", {}, torch.ones(1, 1)
        )
        expected = torch.tensor([[[[0.6, 0.1, 0.3]]]], dtype=torch.float32)
        self.assertTrue(torch.equal(natural, weights))
        self.assertTrue(torch.allclose(swapped, expected))

    def test_padded_positions_are_not_swap_candidates(self):
        weights = torch.tensor([[[[0.0, 0.2, 0.8]]]], dtype=torch.float32)
        sources = torch.tensor([1])
        mask = torch.tensor([[0, 1, 1]])
        patched = routing.patch_attention_weights(
            weights, sources, [0], "source_min", {}, valid_mask=mask
        )
        self.assertTrue(torch.equal(patched, weights))

    def test_custom_backend_recomputes_output_from_patched_weights(self):
        torch.manual_seed(4)
        module = SimpleNamespace(head_dim=3, num_key_value_groups=1, layer_idx=2, training=False)
        query = torch.randn(1, 2, 3, 3)
        key = torch.randn(1, 2, 3, 3)
        value = torch.randn(1, 2, 3, 3)
        routing.PATCH_STATE = {
            "layer": 2,
            "heads": [1],
            "mode": "source_max",
            "sources": torch.tensor([0]),
            "diagnostics": {},
        }
        output, weights = routing.routing_attention_forward(
            module, query, key, value, attention_mask=None, scaling=3 ** -0.5
        )
        expected = torch.matmul(weights, value).transpose(1, 2).contiguous()
        self.assertTrue(torch.allclose(output, expected))
        self.assertEqual(weights[0, 1, -1, 0], weights[0, 1, -1].max())
        self.assertEqual(routing.PATCH_STATE["diagnostics"]["sorted"], 0.0)

    def test_contrast_reports_paired_accuracy_and_margin_intervals(self):
        baseline = {
            "accuracy": 1 / 3,
            "mean_margin": -1 / 3,
            "mean_source_mass": 0.2,
            "records": [
                {"correct": 0.0, "margin": -1.0},
                {"correct": 0.0, "margin": -0.5},
                {"correct": 1.0, "margin": 0.5},
            ]
        }
        intervention = {
            "mode": "source_max",
            "accuracy": 1.0,
            "mean_margin": 2 / 3,
            "mean_source_mass": 0.7,
            "records": [
                {"correct": 1.0, "margin": 0.5},
                {"correct": 1.0, "margin": 0.5},
                {"correct": 1.0, "margin": 1.0},
            ],
        }
        result = routing.contrast(baseline, intervention, seed=7)
        self.assertAlmostEqual(result["accuracy_delta"], 2 / 3)
        self.assertAlmostEqual(result["margin_delta"], 1.0)
        self.assertGreaterEqual(result["accuracy_delta_ci95"][0], 0.0)
        self.assertGreater(result["margin_delta_ci95"][0], 0.0)


if __name__ == "__main__":
    unittest.main()
