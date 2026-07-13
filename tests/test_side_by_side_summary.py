from __future__ import annotations

import unittest

from scripts.summarize_side_by_side_review import summarize


class SideBySideSummaryTests(unittest.TestCase):
    def test_summarize_counts_overall_and_by_label(self):
        rows = [
            {"manual_preferred_setting": "s007", "label": "benign", "suite": "benign"},
            {"manual_preferred_setting": "tie", "label": "jailbreak", "suite": "direct_jailbreak"},
            {"manual_preferred_setting": "neither", "label": "jailbreak", "suite": "direct_jailbreak"},
        ]

        counters = summarize(rows)

        self.assertEqual(counters["overall"]["s007"], 1)
        self.assertEqual(counters["label:jailbreak"]["tie"], 1)
        self.assertEqual(counters["suite:direct_jailbreak"]["neither"], 1)


if __name__ == "__main__":
    unittest.main()
