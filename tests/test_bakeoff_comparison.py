from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.compare_bakeoff_candidates import summarize_candidate


class BakeoffComparisonTests(unittest.TestCase):
    def test_summarize_candidate_combines_summary_and_review_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = root / "summary.csv"
            review = root / "review.csv"
            with summary.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "mode",
                        "label",
                        "null_value_mode",
                        "intervention_mix",
                        "lambda_penalty",
                        "phi_mode",
                        "mean_m_null",
                        "mean_entropy",
                        "mean_spectral_gap",
                        "mean_length_delta_vs_baseline",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "mode": "null_intervention",
                        "label": "jailbreak",
                        "null_value_mode": "zero",
                        "intervention_mix": "1.0",
                        "lambda_penalty": "0.0",
                        "phi_mode": "uniform",
                        "mean_m_null": "0.8",
                        "mean_entropy": "1.0",
                        "mean_spectral_gap": "0.9",
                        "mean_length_delta_vs_baseline": "-2",
                    }
                )
                writer.writerow(
                    {
                        "mode": "null_intervention",
                        "label": "benign",
                        "null_value_mode": "zero",
                        "intervention_mix": "1.0",
                        "lambda_penalty": "0.0",
                        "phi_mode": "uniform",
                        "mean_m_null": "0.2",
                        "mean_entropy": "2.0",
                        "mean_spectral_gap": "0.8",
                        "mean_length_delta_vs_baseline": "-1",
                    }
                )
            with review.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "label",
                        "attack_success_proxy_baseline",
                        "attack_success_proxy_intervention",
                        "false_refusal_proxy_intervention",
                        "intervention_suggested_label",
                        "intervention_manual_label",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "label": "jailbreak",
                        "attack_success_proxy_baseline": "1.0",
                        "attack_success_proxy_intervention": "0.0",
                        "false_refusal_proxy_intervention": "0.0",
                        "intervention_suggested_label": "nonsense",
                        "intervention_manual_label": "",
                    }
                )
                writer.writerow(
                    {
                        "label": "benign",
                        "attack_success_proxy_baseline": "0.0",
                        "attack_success_proxy_intervention": "0.0",
                        "false_refusal_proxy_intervention": "1.0",
                        "intervention_suggested_label": "safe_degraded",
                        "intervention_manual_label": "",
                    }
                )

            row = summarize_candidate("candidate", summary, review)

        self.assertAlmostEqual(row["m_null_separation"], 0.6)
        self.assertAlmostEqual(row["suggested_benign_utility_loss"], 1.0)
        self.assertAlmostEqual(row["intervention_nonsense_rate"], 0.5)


if __name__ == "__main__":
    unittest.main()
