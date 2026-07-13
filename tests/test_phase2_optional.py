from __future__ import annotations

import importlib.util
import unittest

import numpy as np

from thermosafety.real_model import RealModelTrace, hidden_state_features
from thermosafety.trajectory_risk import score_trajectory_risk


class Phase2OptionalTests(unittest.TestCase):
    def test_hidden_state_features_without_hf_dependencies(self):
        trace = RealModelTrace(
            prompt="hello",
            tokens=["hello"],
            hidden_states=[
                np.array([[0.0, 1.0], [1.0, 1.0]]),
                np.array([[0.0, 2.0], [2.0, 2.0]]),
            ],
            attentions=[
                np.array([[[0.7, 0.3], [0.2, 0.8]]]),
            ],
        )
        features = hidden_state_features(trace)

        self.assertIn("hidden_token_drift", features)
        self.assertIn("native_attention_entropy", features)
        self.assertGreater(features["hidden_token_drift"], 0.0)

    def test_trajectory_risk_modes_without_hf_dependencies(self):
        trace = RealModelTrace(
            prompt="Describe AI safety research on jailbreak prevention in non-operational terms.",
            tokens=["Describe", "AI", "safety"],
            hidden_states=[
                np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]]),
                np.array([[0.5, 0.0], [1.5, 0.0], [2.0, 1.0]]),
            ],
            attentions=[
                np.array([[[0.8, 0.2, 0.0], [0.1, 0.8, 0.1], [0.3, 0.3, 0.4]]]),
            ],
        )

        mixed = score_trajectory_risk(trace, mode="mixed")
        trajectory = score_trajectory_risk(trace, mode="trajectory")
        self.assertGreaterEqual(mixed.score, 0.0)
        self.assertLessEqual(mixed.score, 1.0)
        self.assertGreaterEqual(trajectory.hidden_drift_score, 0.0)

    @unittest.skipUnless(
        importlib.util.find_spec("torch") and importlib.util.find_spec("transformers"),
        "torch/transformers are optional Phase 2 dependencies",
    )
    def test_hf_import_path_when_dependencies_exist(self):
        from thermosafety.real_model import _load_hf_modules

        torch, auto_model, auto_tokenizer = _load_hf_modules()
        self.assertIsNotNone(torch)
        self.assertIsNotNone(auto_model)
        self.assertIsNotNone(auto_tokenizer)


if __name__ == "__main__":
    unittest.main()
