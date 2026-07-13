from __future__ import annotations

import importlib.util
import unittest

import numpy as np

from thermosafety.attention import NullAttractorConfig


@unittest.skipUnless(importlib.util.find_spec("torch"), "torch is optional for intervention tests")
class InterventionTests(unittest.TestCase):
    def test_null_attractor_attention_forward_shapes_and_logs(self):
        import torch

        from thermosafety.intervention import InterventionLog, null_attractor_attention_forward

        class Module:
            training = False
            layer_idx = 3

        batch, heads, query_len, key_len, dim = 2, 4, 5, 5, 8
        query = torch.randn(batch, heads, query_len, dim)
        key = torch.randn(batch, heads, key_len, dim)
        value = torch.randn(batch, heads, key_len, dim)
        log = InterventionLog()

        output, weights = null_attractor_attention_forward(
            Module(),
            query,
            key,
            value,
            attention_mask=None,
            risk=0.9,
            config=NullAttractorConfig(risk_threshold=0.2, eta_null=5.0),
            log=log,
        )

        self.assertEqual(tuple(output.shape), (batch, query_len, heads, dim))
        self.assertEqual(tuple(weights.shape), (batch, heads, query_len, key_len))
        self.assertEqual(len(log.records), heads)
        self.assertGreater(log.mean_null_mass(), 0.0)

    def test_selected_layers_delegate_without_logging(self):
        import torch

        from thermosafety.intervention import InterventionLog, null_attractor_attention_forward

        class Config:
            _attn_implementation = "eager"

        class Module:
            training = False
            layer_idx = 1
            config = Config()

        query = torch.randn(1, 2, 3, 4)
        key = torch.randn(1, 2, 3, 4)
        value = torch.randn(1, 2, 3, 4)
        log = InterventionLog()

        output, weights = null_attractor_attention_forward(
            Module(),
            query,
            key,
            value,
            attention_mask=None,
            risk=0.9,
            config=NullAttractorConfig(),
            log=log,
            selected_layers={2},
        )

        self.assertEqual(tuple(output.shape), (1, 3, 2, 4))
        self.assertEqual(tuple(weights.shape), (1, 2, 3, 3))
        self.assertEqual(len(log.records), 0)

    def test_contextual_null_value_logs_nonzero_norm(self):
        import torch

        from thermosafety.intervention import InterventionLog, null_attractor_attention_forward

        class Module:
            training = False
            layer_idx = 2

        query = torch.randn(1, 2, 3, 4)
        key = torch.randn(1, 2, 3, 4)
        value = torch.randn(1, 2, 3, 4)
        log = InterventionLog()

        null_attractor_attention_forward(
            Module(),
            query,
            key,
            value,
            attention_mask=None,
            risk=0.9,
            config=NullAttractorConfig(risk_threshold=0.2, null_value_mode="context_mean"),
            log=log,
        )

        self.assertGreater(log.mean("null_value_norm"), 0.0)
        self.assertIn("entropy", log.records[0])
        self.assertIn("spectral_gap", log.records[0])

    def test_selected_heads_only_intervene_on_requested_heads(self):
        import torch

        from thermosafety.intervention import InterventionLog, null_attractor_attention_forward

        class Module:
            training = False
            layer_idx = 2

        query = torch.randn(1, 3, 3, 4)
        key = torch.randn(1, 3, 3, 4)
        value = torch.randn(1, 3, 3, 4)
        log = InterventionLog()

        null_attractor_attention_forward(
            Module(),
            query,
            key,
            value,
            attention_mask=None,
            risk=0.9,
            config=NullAttractorConfig(risk_threshold=0.2, eta_null=5.0),
            log=log,
            selected_heads={1},
        )

        selected = {int(record["head"]): record for record in log.records}
        self.assertEqual(selected[0]["head_selected"], 0.0)
        self.assertEqual(selected[1]["head_selected"], 1.0)
        self.assertEqual(selected[2]["head_selected"], 0.0)
        self.assertGreater(selected[1]["m_null"], selected[0]["m_null"])

    def test_build_null_logits_zero_mode_ignores_base_logits(self):
        import torch

        from thermosafety.intervention import build_null_logits

        base_logits = torch.tensor([[[[10.0, -5.0, 3.0]]]])
        null_logits = build_null_logits(base_logits, None, NullAttractorConfig(null_key_mode="zero"), torch)

        self.assertEqual(tuple(null_logits.shape), (1, 1, 1, 1))
        self.assertAlmostEqual(float(null_logits[0, 0, 0, 0]), 0.0, places=6)

    def test_build_null_logits_zero_mode_respects_null_key_scale(self):
        import torch

        from thermosafety.intervention import build_null_logits

        base_logits = torch.tensor([[[[10.0, -5.0, 3.0]]]])
        null_logits = build_null_logits(
            base_logits, None, NullAttractorConfig(null_key_mode="zero", null_key_scale=2.5), torch
        )

        self.assertAlmostEqual(float(null_logits[0, 0, 0, 0]), 2.5, places=6)

    def test_build_null_logits_mean_logit_mode_matches_unmasked_mean(self):
        import torch

        from thermosafety.intervention import build_null_logits

        base_logits = torch.tensor([[[[10.0, -5.0, 3.0]]]])
        null_logits = build_null_logits(base_logits, None, NullAttractorConfig(null_key_mode="mean_logit"), torch)

        self.assertAlmostEqual(float(null_logits[0, 0, 0, 0]), (10.0 - 5.0 + 3.0) / 3.0, places=6)

    def test_build_null_logits_mean_logit_mode_self_normalizes_across_scale(self):
        """The core bug fix: a flat +1000 or -1000 logit shift should not change the null slot's
        relative competitiveness once mean_logit mode is used, unlike zero mode."""
        import torch

        from thermosafety.intervention import build_null_logits

        low_scale = torch.tensor([[[[1.0, 2.0, 3.0]]]])
        high_scale = torch.tensor([[[[1001.0, 1002.0, 1003.0]]]])
        cfg = NullAttractorConfig(null_key_mode="mean_logit")

        null_low = build_null_logits(low_scale, None, cfg, torch)
        null_high = build_null_logits(high_scale, None, cfg, torch)

        self.assertAlmostEqual(float(null_low[0, 0, 0, 0]), 2.0, places=6)
        self.assertAlmostEqual(float(null_high[0, 0, 0, 0]), 1002.0, places=6)
        # In both cases the null logit sits exactly at the mean of the real logits -- i.e. it is
        # always exactly as competitive as an "average" real key, regardless of absolute scale.
        self.assertAlmostEqual(float(null_low[0, 0, 0, 0] - low_scale.mean()), 0.0, places=6)
        self.assertAlmostEqual(float(null_high[0, 0, 0, 0] - high_scale.mean()), 0.0, places=6)

    def test_build_null_logits_mean_logit_mode_respects_causal_mask(self):
        import torch

        from thermosafety.intervention import build_null_logits

        base_logits = torch.tensor([[[[10.0, -5.0, 3.0]]]])
        # Only the first key is causally valid; masked positions carry a large negative value.
        mask = torch.tensor([[[[0.0, torch.finfo(torch.float32).min, torch.finfo(torch.float32).min]]]])
        null_logits = build_null_logits(base_logits, mask, NullAttractorConfig(null_key_mode="mean_logit"), torch)

        self.assertAlmostEqual(float(null_logits[0, 0, 0, 0]), 10.0, places=4)

    def test_build_null_logits_unknown_mode_raises(self):
        import torch

        from thermosafety.intervention import build_null_logits

        base_logits = torch.zeros(1, 1, 1, 2)
        with self.assertRaises(ValueError):
            build_null_logits(base_logits, None, NullAttractorConfig(null_key_mode="bogus"), torch)

    def test_mean_logit_mode_flattens_layer_baseline_null_mass(self):
        """End-to-end regression for the fix: at risk=0 (gate off), zero-mode null mass should
        track the base logits' absolute scale, while mean_logit-mode null mass should stay
        pinned near a uniform share regardless of that scale.

        Uses a deterministic scenario (identical key vector at every position) so every real
        logit is equal to a controlled value `L`, making the prediction exact: zero-mode
        competes a fixed 0 against `L`, so a very negative `L` should make the null slot
        dominate; mean_logit-mode sets the null logit to `L` itself (the mean of equal values),
        so it should land exactly at a uniform share regardless of how negative `L` is.
        """
        import torch

        from thermosafety.intervention import InterventionLog, null_attractor_attention_forward

        class Module:
            training = False
            layer_idx = 0

        seq_len, dim, heads = 6, 8, 2
        query = torch.ones(1, heads, seq_len, dim)
        key = torch.full((1, heads, seq_len, dim), -50.0)
        value = torch.randn(1, heads, seq_len, dim)

        zero_log = InterventionLog()
        null_attractor_attention_forward(
            Module(), query, key, value, attention_mask=None, risk=0.0,
            config=NullAttractorConfig(risk_threshold=0.9, null_key_mode="zero"), log=zero_log,
        )
        mean_log = InterventionLog()
        null_attractor_attention_forward(
            Module(), query, key, value, attention_mask=None, risk=0.0,
            config=NullAttractorConfig(risk_threshold=0.9, null_key_mode="mean_logit"), log=mean_log,
        )

        uniform_share = 1.0 / (seq_len + 1)
        # zero-mode: a flat logit of 0 against a uniformly very negative real landscape dominates.
        self.assertGreater(zero_log.mean_null_mass(), 0.99)
        # mean_logit-mode: self-normalized, lands exactly at a uniform share instead.
        self.assertAlmostEqual(mean_log.mean_null_mass(), uniform_share, places=4)

    def test_unsafe_coupling_barrier_penalizes_aligned_couplings(self):
        import torch

        from thermosafety.intervention import InterventionLog, null_attractor_attention_forward

        class Module:
            training = False
            layer_idx = 2

        torch.manual_seed(0)
        query = torch.randn(1, 2, 4, 6)
        key = torch.randn(1, 2, 4, 6)
        value = torch.randn(1, 2, 4, 6)
        # unsafe directions in q/k space
        u = torch.randn(2, 6)
        barrier = {2: {"u_q": torch.nn.functional.normalize(u, dim=-1),
                       "u_k": torch.nn.functional.normalize(u, dim=-1)}}
        log = InterventionLog()

        # With eta=0 (no null bias) and lambda>0, the only effect is the barrier penalty.
        cfg = NullAttractorConfig(
            risk_threshold=0.2, eta_null=0.0, lambda_penalty=0.5,
            phi_mode="unsafe_coupling", null_value_mode="zero",
        )
        null_attractor_attention_forward(
            Module(), query, key, value, attention_mask=None, risk=0.9,
            config=cfg, log=log, barrier_bank=barrier,
        )
        # The barrier produced a nonzero mean penalty (unsafe couplings were raised in energy).
        self.assertGreater(abs(log.mean("phi_penalty_mean")), 0.0)

    def test_unsafe_coupling_requires_barrier_query_key(self):
        from thermosafety.attention import NullAttractorConfig as Cfg
        from thermosafety.intervention import phi_penalty
        import torch

        base = torch.randn(1, 2, 3, 3)
        with self.assertRaises(ValueError):
            phi_penalty(base, 0.9, Cfg(lambda_penalty=0.5, phi_mode="unsafe_coupling"), torch)

    def test_grouped_query_attention_expands_kv_heads_to_match_query(self):
        import torch

        from thermosafety.intervention import InterventionLog, null_attractor_attention_forward

        class Module:
            training = False
            layer_idx = 2

        batch, query_heads, kv_heads, seq_len, dim = 1, 4, 2, 3, 8
        query = torch.randn(batch, query_heads, seq_len, dim)
        key = torch.randn(batch, kv_heads, seq_len, dim)
        value = torch.randn(batch, kv_heads, seq_len, dim)
        log = InterventionLog()

        output, weights = null_attractor_attention_forward(
            Module(),
            query,
            key,
            value,
            attention_mask=None,
            risk=0.9,
            config=NullAttractorConfig(risk_threshold=0.2, eta_null=5.0),
            log=log,
        )

        self.assertEqual(tuple(output.shape), (batch, seq_len, query_heads, dim))
        self.assertEqual(tuple(weights.shape), (batch, query_heads, seq_len, seq_len))
        self.assertEqual(len(log.records), query_heads)

    def test_grouped_query_attention_delegate_path_also_expands_kv_heads(self):
        import torch

        from thermosafety.intervention import InterventionLog, null_attractor_attention_forward

        class Config:
            _attn_implementation = "eager"

        class Module:
            training = False
            layer_idx = 1
            config = Config()

        query = torch.randn(1, 4, 3, 8)
        key = torch.randn(1, 2, 3, 8)
        value = torch.randn(1, 2, 3, 8)
        log = InterventionLog()

        output, weights = null_attractor_attention_forward(
            Module(),
            query,
            key,
            value,
            attention_mask=None,
            risk=0.9,
            config=NullAttractorConfig(),
            log=log,
            selected_layers={2},
        )

        self.assertEqual(tuple(output.shape), (1, 3, 4, 8))
        self.assertEqual(tuple(weights.shape), (1, 4, 3, 3))
        self.assertEqual(len(log.records), 0)

    def test_calibrated_refusal_null_value_uses_bank(self):
        import torch

        from thermosafety.intervention import InterventionLog, null_attractor_attention_forward

        class Module:
            training = False
            layer_idx = 2

        query = torch.randn(1, 2, 3, 4)
        key = torch.randn(1, 2, 3, 4)
        value = torch.zeros(1, 2, 3, 4)
        bank = {2: torch.ones(2, 4)}
        log = InterventionLog()

        null_attractor_attention_forward(
            Module(),
            query,
            key,
            value,
            attention_mask=None,
            risk=0.9,
            config=NullAttractorConfig(risk_threshold=0.2, null_value_mode="calibrated_refusal"),
            log=log,
            null_value_bank=bank,
        )

        self.assertGreater(log.mean("null_value_norm"), 0.0)

    def test_semantic_refusal_null_value_uses_refusal_minus_unsafe_bank(self):
        import torch

        from thermosafety.intervention import InterventionLog, null_attractor_attention_forward

        class Module:
            training = False
            layer_idx = 2

        query = torch.randn(1, 2, 3, 4)
        key = torch.randn(1, 2, 3, 4)
        value = torch.zeros(1, 2, 3, 4)
        bank = {
            2: {
                "refusal": torch.ones(2, 4),
                "unsafe": torch.zeros(2, 4),
                "redirect": torch.full((2, 4), 0.5),
            }
        }
        log = InterventionLog()

        null_attractor_attention_forward(
            Module(),
            query,
            key,
            value,
            attention_mask=None,
            risk=0.9,
            config=NullAttractorConfig(
                risk_threshold=0.2,
                null_value_mode="semantic_refusal",
                semantic_attractor_strength=1.0,
            ),
            log=log,
            null_value_bank=bank,
        )

        self.assertGreater(log.mean("null_value_norm"), 0.0)

    def test_semantic_redirection_accepts_anchor_bank(self):
        import torch

        from thermosafety.intervention import InterventionLog, null_attractor_attention_forward

        class Module:
            training = False
            layer_idx = 2

        query = torch.randn(1, 2, 3, 4)
        key = torch.randn(1, 2, 3, 4)
        value = torch.zeros(1, 2, 3, 4)
        bank = {
            2: {
                "refusal": torch.ones(2, 4),
                "unsafe": torch.zeros(2, 4),
                "redirect": torch.full((2, 4), 0.25),
            }
        }
        log = InterventionLog()

        null_attractor_attention_forward(
            Module(),
            query,
            key,
            value,
            attention_mask=None,
            risk=0.4,
            config=NullAttractorConfig(
                risk_threshold=0.2,
                null_value_mode="semantic_redirection",
                semantic_attractor_strength=0.5,
                redirect_risk_threshold=0.75,
            ),
            log=log,
            null_value_bank=bank,
        )

        self.assertGreater(log.mean("null_value_norm"), 0.0)


if __name__ == "__main__":
    unittest.main()
