from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.summarize_paper_evidence import build_report


class PaperEvidenceTests(unittest.TestCase):
    def test_build_report_contains_required_evidence_categories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "phase_transition": root / "phase.md",
                "baseline_comparison": root / "baseline.md",
                "latent_probe": root / "latent.md",
                "intervention_failure": root / "failure.md",
                "selected_heads": root / "heads.md",
                "related_work": root / "related.md",
            }
            files["phase_transition"].write_text(
                "# Phase\n\n| setting | jump |\n|---|---:|\n| toy | 0.9 |\n",
                encoding="utf-8",
            )
            files["baseline_comparison"].write_text(
                "# Baseline\n\n| method | thermodynamic observables |\n|---|---|\n| null_attractor | yes |\n",
                encoding="utf-8",
            )
            files["latent_probe"].write_text(
                "# Latent\n\n## Focused threshold sweep\n\n| threshold | separation |\n|---:|---:|\n| 0.60 | 0.289 |\n",
                encoding="utf-8",
            )
            files["intervention_failure"].write_text(
                "# Failure\n\n## Interpretation\n\nHigh null mass is not safe generation.\n",
                encoding="utf-8",
            )
            files["selected_heads"].write_text(
                "# Heads\n\n## Head Ranking\n\n| head | separation |\n|---:|---:|\n| 10 | 0.396 |\n\n## Selected-Head Grid\n\n| heads | separation |\n|---|---:|\n| 10,14 | 0.048 |\n",
                encoding="utf-8",
            )
            files["related_work"].write_text(
                "# Related\n\n## One-Sentence Positioning\n\nWe turn attention-as-energy theory into a safety diagnostic.\n",
                encoding="utf-8",
            )

            report = build_report(files)

        self.assertIn("Toy and Real Phase-Transition Evidence", report)
        self.assertIn("Key Paper Move", report)
        self.assertIn("structured attractors or barriers", report)
        self.assertIn("Threshold Baseline Comparison", report)
        self.assertIn("Latent Trajectory Risk Probe", report)
        self.assertIn("Attractor Derivation Scaffold", report)
        self.assertIn("Negative Control: Intervention Failure", report)
        self.assertIn("not defense results", report)
        self.assertIn("Selected-Head Diagnostic Ablation", report)
        self.assertIn("Related-Work Anchor", report)
        self.assertIn("Not OK: claiming current intervention prevents jailbreaks", report)


if __name__ == "__main__":
    unittest.main()
