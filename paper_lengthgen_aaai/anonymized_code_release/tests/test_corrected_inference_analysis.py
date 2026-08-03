from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze_corrected_inference as audit  # noqa: E402


def test_exact_sign_flip_uses_cluster_level_two_sided_tail():
    assert audit.exact_sign_flip([1.0, 1.0, 1.0]) == 0.25
    assert audit.exact_sign_flip([1.0, -1.0]) == 1.0


def test_holm_adjustment_is_monotone_in_sorted_p_values():
    rows = [
        {"p_two_sided": 0.01},
        {"p_two_sided": 0.04},
        {"p_two_sided": 0.03},
    ]
    audit.holm_adjust(rows)
    ordered = sorted(rows, key=lambda row: row["p_two_sided"])
    adjusted = [row["p_holm"] for row in ordered]
    assert adjusted == sorted(adjusted)
    assert all(row["p_holm"] >= row["p_two_sided"] for row in rows)


def test_saved_audits_use_independent_cluster_units():
    assignment = audit.assignment_primary()
    capacity = audit.capacity_primary()
    natural = audit.natural_transfer()
    assert assignment["n_clusters"] == 16
    assert capacity["n_clusters"] == 16
    assert natural["n_clusters"] == 6
    assert natural["p_two_sided"] == 0.03125


def test_vacuity_is_reported_at_head_and_complete_circuit_levels():
    result = audit.vacuity_audit()
    assert result["all_selected_heads_vacuous_fraction"] < result["head_example_vacuous_fraction"]
    assert result["active_circuit_count"] + result["all_selected_heads_vacuous_count"] == result["n_examples"]


def test_ceiling_robust_association_reports_rank_statistics():
    result = audit.ceiling_robust_association()
    assert result["ceiling_count"] > 0
    assert result["attention"]["spearman"] > result["variance"]["spearman"]
    assert result["attention"]["non_ceiling_spearman"] > result["variance"]["non_ceiling_spearman"]
