from __future__ import annotations

import unittest

from scripts.rank_intervention_settings import rank_settings


class RankInterventionSettingsTests(unittest.TestCase):
    def test_rank_prefers_lower_utility_loss_over_raw_null_mass(self):
        summary_rows = [
            {
                "setting_id": "blunt",
                "mode": "null_intervention",
                "layers": "5",
                "heads": "all",
                "risk_threshold": "0.26",
                "eta_null": "4.0",
                "beta_collapse": "2.5",
                "lambda_penalty": "0.0",
                "null_value_mode": "calibrated_refusal",
                "intervention_mix": "1.0",
                "phi_mode": "positive_logits",
                "label": "jailbreak",
                "mean_m_null": "0.8",
                "mean_entropy": "1.0",
                "mean_spectral_gap": "0.9",
                "mean_length_delta_vs_baseline": "-5",
            },
            {
                "setting_id": "blunt",
                "mode": "null_intervention",
                "layers": "5",
                "heads": "all",
                "risk_threshold": "0.26",
                "eta_null": "4.0",
                "beta_collapse": "2.5",
                "lambda_penalty": "0.0",
                "null_value_mode": "calibrated_refusal",
                "intervention_mix": "1.0",
                "phi_mode": "positive_logits",
                "label": "benign",
                "mean_m_null": "0.1",
                "mean_entropy": "1.0",
                "mean_spectral_gap": "0.9",
                "mean_length_delta_vs_baseline": "-5",
            },
            {
                "setting_id": "gentle",
                "mode": "null_intervention",
                "layers": "5",
                "heads": "all",
                "risk_threshold": "0.42",
                "eta_null": "2.5",
                "beta_collapse": "1.5",
                "lambda_penalty": "0.0",
                "null_value_mode": "calibrated_refusal",
                "intervention_mix": "0.5",
                "phi_mode": "positive_logits",
                "label": "jailbreak",
                "mean_m_null": "0.5",
                "mean_entropy": "2.0",
                "mean_spectral_gap": "0.8",
                "mean_length_delta_vs_baseline": "-1",
            },
            {
                "setting_id": "gentle",
                "mode": "null_intervention",
                "layers": "5",
                "heads": "all",
                "risk_threshold": "0.42",
                "eta_null": "2.5",
                "beta_collapse": "1.5",
                "lambda_penalty": "0.0",
                "null_value_mode": "calibrated_refusal",
                "intervention_mix": "0.5",
                "phi_mode": "positive_logits",
                "label": "benign",
                "mean_m_null": "0.05",
                "mean_entropy": "2.0",
                "mean_spectral_gap": "0.8",
                "mean_length_delta_vs_baseline": "-1",
            },
        ]
        review_rows = [
            {
                "setting_id": "blunt",
                "label": "benign",
                "intervention_suggested_label": "nonsense",
                "intervention_manual_label": "",
                "attack_success_proxy_intervention": "0",
                "false_refusal_proxy_intervention": "0",
            },
            {
                "setting_id": "blunt",
                "label": "jailbreak",
                "intervention_suggested_label": "nonsense",
                "intervention_manual_label": "",
                "attack_success_proxy_intervention": "0",
                "false_refusal_proxy_intervention": "0",
            },
            {
                "setting_id": "gentle",
                "label": "benign",
                "intervention_suggested_label": "safe_useful",
                "intervention_manual_label": "",
                "attack_success_proxy_intervention": "0",
                "false_refusal_proxy_intervention": "0",
            },
            {
                "setting_id": "gentle",
                "label": "jailbreak",
                "intervention_suggested_label": "safe_useful",
                "intervention_manual_label": "",
                "attack_success_proxy_intervention": "0",
                "false_refusal_proxy_intervention": "0",
            },
        ]

        ranked = rank_settings(summary_rows, review_rows)

        self.assertEqual(ranked[0]["setting_id"], "gentle")


if __name__ == "__main__":
    unittest.main()
