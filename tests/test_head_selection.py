from __future__ import annotations

import unittest

from scripts.select_heads_by_risk_separation import rank_heads


class HeadSelectionTests(unittest.TestCase):
    def test_rank_heads_rewards_separation_and_penalizes_benign_mass(self):
        rows = [
            {"layer": "5", "head": "0", "label": "jailbreak", "m_null": "0.8"},
            {"layer": "5", "head": "0", "label": "benign", "m_null": "0.1"},
            {"layer": "5", "head": "1", "label": "jailbreak", "m_null": "0.9"},
            {"layer": "5", "head": "1", "label": "benign", "m_null": "0.6"},
        ]

        ranked = rank_heads(rows, benign_penalty=0.5)

        self.assertEqual(ranked[0]["head"], 0)
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])


if __name__ == "__main__":
    unittest.main()
