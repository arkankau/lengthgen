from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "colab"))
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_pretrained_natural_mcqa as natural_analysis  # noqa: E402
import analyze_qwen_exact_replication as qwen_analysis  # noqa: E402
import pretrained_endogenous_assignment as endogenous  # noqa: E402


def test_distractor_permutation_holds_source_position_and_answer_fixed():
    keys = [10, 11, 12, 13]
    values = [20, 21, 22, 23]
    first = endogenous.render_variant(
        keys, values, target=2, source_slot=1, separator=[30], terminator=[31], order=[0, 1, 3]
    )
    second = endogenous.render_variant(
        keys, values, target=2, source_slot=1, separator=[30], terminator=[31], order=[3, 0, 1]
    )
    assert first[1] == second[1]
    assert first[2] == second[2] == 22
    assert sorted(first[0]) == sorted(second[0])


def test_matching_uses_minimum_spectrum_distance_after_frozen_gap_gate():
    records = [
        {"base_id": 0, "variant_id": 0, "source_mass": 0.10, "margin": 0.0,
         "correct": 0.0, "max_weight": 0.5, "entropy": 1.0},
        {"base_id": 0, "variant_id": 1, "source_mass": 0.12, "margin": 1.0,
         "correct": 1.0, "max_weight": 0.5, "entropy": 1.0},
        {"base_id": 0, "variant_id": 2, "source_mass": 0.30, "margin": 5.0,
         "correct": 1.0, "max_weight": 0.7, "entropy": 0.8},
    ]
    spectra = np.asarray([
        [[0.6, 0.4]],
        [[0.59, 0.41]],
        [[0.9, 0.1]],
    ])
    matched = endogenous.matched_pairs(records, spectra, minimum_source_gap=0.01)
    assert len(matched) == 1
    assert matched[0]["high_variant"] == 1
    assert matched[0]["low_variant"] == 0
    assert np.isclose(matched[0]["margin_delta"], 1.0)


def test_fixed_effects_recovers_within_base_source_relation():
    records = []
    for base in range(5):
        for variant, source in enumerate((0.1, 0.2, 0.3, 0.4)):
            records.append({
                "base_id": base,
                "source_mass": source,
                "max_weight": 0.5 + 0.01 * variant,
                "entropy": 1.0 - 0.01 * variant,
                "margin": 3.0 * source + base,
            })
    coefficient = endogenous.fixed_effects_coefficients(records)
    assert coefficient["source_mass"] > 0


def test_six_consistent_seeds_can_reach_two_sided_significance():
    assert qwen_analysis.exact_sign_flip([1, 1, 1, 1, 1, 1]) == 0.03125
    assert natural_analysis.exact_sign_flip([1, 1, 1, 1, 1, 1]) == 0.03125
