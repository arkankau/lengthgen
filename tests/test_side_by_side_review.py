from __future__ import annotations

import unittest

from scripts.make_side_by_side_review import make_rows


class SideBySideReviewTests(unittest.TestCase):
    def test_make_rows_pairs_settings_by_prompt_id(self):
        review_rows = [
            {
                "setting_id": "a",
                "id": "p1",
                "suite": "benign",
                "label": "benign",
                "risk": "0.1",
                "prompt": "Prompt",
                "baseline_continuation": "base",
                "mean_m_null": "0.2",
                "intervention_suggested_label": "safe_useful",
                "length_delta": "-1",
                "intervention_continuation": "a text",
            },
            {
                "setting_id": "b",
                "id": "p1",
                "suite": "benign",
                "label": "benign",
                "risk": "0.1",
                "prompt": "Prompt",
                "baseline_continuation": "base",
                "mean_m_null": "0.1",
                "intervention_suggested_label": "safe_degraded",
                "length_delta": "-2",
                "intervention_continuation": "b text",
            },
        ]

        rows = make_rows(review_rows, "a", "b")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["setting_a_continuation"], "a text")
        self.assertEqual(rows[0]["setting_b_continuation"], "b text")


if __name__ == "__main__":
    unittest.main()
