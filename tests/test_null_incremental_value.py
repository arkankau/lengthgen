from __future__ import annotations

import unittest

from scripts.audit_null_incremental_value import audit_rows, target_rows


def make_row(idx: int, label: str = "benign") -> dict[str, object]:
    risk = float(idx)
    thermo = 1.0 if idx % 2 else -1.0
    return {
        "source": "synthetic.csv",
        "setting_id": "s001",
        "id": f"case-{idx}",
        "suite": "benign" if label == "benign" else "direct_jailbreak",
        "label": label,
        "risk": risk,
        "eta_null": risk,
        "lambda_penalty": 0.0,
        "intervention_mix": 1.0,
        "layer_value": 1.0,
        "semantic_mode": 0.0,
        "barrier_mode": 0.0,
        "mean_m_null": thermo,
        "mean_entropy": 0.0,
        "mean_psi": 0.0,
        "mean_spectral_gap": 0.0,
        "thermo_collapse": 0.0,
        "benign_damage": float(label == "benign" and idx > 7),
        "jailbreak_unsafe": float(label == "jailbreak" and idx > 7),
        "jailbreak_safe_refusal": float(label == "jailbreak" and idx < 3),
        "collapse_failure": float(idx > 8),
        "utility_loss": risk + thermo,
        "coherence": 1.0 - (0.01 * risk) - (0.05 * thermo),
    }


class NullIncrementalValueTests(unittest.TestCase):
    def test_target_rows_filters_label_specific_targets(self):
        rows = [make_row(0, "benign"), make_row(1, "jailbreak")]

        self.assertEqual(len(target_rows(rows, "benign_damage")), 1)
        self.assertEqual(target_rows(rows, "benign_damage")[0]["label"], "benign")
        self.assertEqual(len(target_rows(rows, "jailbreak_unsafe")), 1)
        self.assertEqual(target_rows(rows, "jailbreak_unsafe")[0]["label"], "jailbreak")
        self.assertEqual(len(target_rows(rows, "collapse_failure")), 2)

    def test_audit_rows_detects_known_extra_thermo_signal(self):
        rows = [make_row(idx, "benign") for idx in range(12)]

        audit = {(row["scope"], row["target"]): row for row in audit_rows(rows)}

        utility = audit[("pooled", "utility_loss")]
        self.assertGreater(float(utility["delta_r2"]), 0.05)
        self.assertEqual(utility["best_feature"], "mean_m_null")


if __name__ == "__main__":
    unittest.main()
