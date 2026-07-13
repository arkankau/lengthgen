from __future__ import annotations

import unittest

import numpy as np

from thermosafety.basin_energy import (
    BasinCentroids,
    basin_energies,
    basin_entropy,
    basin_selectivity,
    boltzmann_occupancy,
    build_refusal_subspace,
    competition_margin,
    cosine,
    energy_to_anchor,
    free_energy,
    mean_anchor,
    orient_basis,
    residual_subspace_coupling,
    signed_axis_projection,
    subspace_alignment,
    subspace_energy,
)


class CosineAndEnergyTests(unittest.TestCase):
    def test_cosine_identical_vectors_is_one(self):
        v = np.array([1.0, 2.0, 3.0])
        self.assertAlmostEqual(cosine(v, v), 1.0, places=6)

    def test_cosine_orthogonal_vectors_is_zero(self):
        self.assertAlmostEqual(cosine(np.array([1.0, 0.0]), np.array([0.0, 1.0])), 0.0, places=6)

    def test_cosine_zero_vector_is_safe(self):
        self.assertEqual(cosine(np.zeros(3), np.array([1.0, 1.0, 1.0])), 0.0)

    def test_energy_to_anchor_is_lower_when_aligned(self):
        anchor = np.array([1.0, 0.0])
        aligned = energy_to_anchor(np.array([2.0, 0.0]), anchor)
        opposed = energy_to_anchor(np.array([-2.0, 0.0]), anchor)
        self.assertLess(aligned, opposed)
        self.assertAlmostEqual(aligned, -1.0, places=6)
        self.assertAlmostEqual(opposed, 1.0, places=6)


class BasinOccupancyTests(unittest.TestCase):
    def test_lower_energy_basin_gets_higher_occupancy(self):
        occupancy = boltzmann_occupancy({"safe": -1.0, "unsafe": 1.0}, temperature=1.0)
        self.assertGreater(occupancy["safe"], occupancy["unsafe"])
        self.assertAlmostEqual(sum(occupancy.values()), 1.0, places=6)

    def test_equal_energies_give_equal_occupancy(self):
        occupancy = boltzmann_occupancy({"safe": 0.5, "unsafe": 0.5, "benign": 0.5}, temperature=1.0)
        for value in occupancy.values():
            self.assertAlmostEqual(value, 1.0 / 3.0, places=6)

    def test_low_temperature_sharpens_occupancy(self):
        cool = boltzmann_occupancy({"safe": -1.0, "unsafe": 1.0}, temperature=0.1)
        warm = boltzmann_occupancy({"safe": -1.0, "unsafe": 1.0}, temperature=10.0)
        self.assertGreater(cool["safe"], warm["safe"])

    def test_temperature_must_be_positive(self):
        with self.assertRaises(ValueError):
            boltzmann_occupancy({"safe": 0.0}, temperature=0.0)

    def test_basin_entropy_is_zero_for_degenerate_occupancy(self):
        self.assertAlmostEqual(basin_entropy({"safe": 1.0, "unsafe": 1e-15}), 0.0, places=4)

    def test_basin_entropy_is_maximal_for_uniform_occupancy(self):
        uniform = {"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25}
        self.assertAlmostEqual(basin_entropy(uniform), np.log(4), places=6)


class FreeEnergyAndMarginTests(unittest.TestCase):
    def test_free_energy_decreases_as_a_basin_deepens(self):
        shallow = free_energy({"safe": -0.1, "unsafe": 0.1}, temperature=1.0)
        deep = free_energy({"safe": -2.0, "unsafe": 0.1}, temperature=1.0)
        self.assertLess(deep, shallow)

    def test_competition_margin_sign(self):
        safe_favored = competition_margin({"safe": -1.0, "unsafe": 0.5})
        unsafe_favored = competition_margin({"safe": 0.5, "unsafe": -1.0})
        self.assertGreater(safe_favored, 0.0)
        self.assertLess(unsafe_favored, 0.0)

    def test_basin_selectivity_separates_jailbreak_from_benign(self):
        margins = [1.0, 0.9, -0.2, -0.1]
        labels = [True, True, False, False]
        sep = basin_selectivity(margins, labels)
        self.assertAlmostEqual(sep, 0.95 - (-0.15), places=6)

    def test_basin_selectivity_handles_missing_class(self):
        self.assertEqual(basin_selectivity([1.0, 2.0], [True, True]), 0.0)


class BasinCentroidsTests(unittest.TestCase):
    def test_basin_energies_maps_over_all_anchors(self):
        centroids = BasinCentroids(
            anchors={
                "safe": np.array([1.0, 0.0]),
                "unsafe": np.array([0.0, 1.0]),
                "benign": np.array([1.0, 1.0]),
            }
        )
        energies = basin_energies(np.array([1.0, 0.0]), centroids)
        self.assertEqual(set(energies), {"safe", "unsafe", "benign"})
        self.assertLess(energies["safe"], energies["unsafe"])

    def test_mean_anchor_is_unit_norm(self):
        anchor = mean_anchor([np.array([1.0, 0.0]), np.array([2.0, 0.0])])
        self.assertAlmostEqual(float(np.linalg.norm(anchor)), 1.0, places=6)

    def test_mean_anchor_requires_input(self):
        with self.assertRaises(ValueError):
            mean_anchor([])


class SubspaceTests(unittest.TestCase):
    def test_single_direction_subspace_matches_cosine_energy(self):
        direction = np.array([1.0, 0.0, 0.0])
        basis = build_refusal_subspace([direction], k=1)
        h = np.array([3.0, 4.0, 0.0])
        alignment = subspace_alignment(h, basis)
        self.assertAlmostEqual(alignment, abs(cosine(h, direction)), places=6)

    def test_orthogonal_diff_vectors_need_two_dimensional_subspace(self):
        diffs = [np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0])]
        basis_1d = build_refusal_subspace(diffs, k=1)
        basis_2d = build_refusal_subspace(diffs, k=2)
        h = np.array([1.0, 1.0, 0.0]) / np.sqrt(2)
        alignment_1d = subspace_alignment(h, basis_1d)
        alignment_2d = subspace_alignment(h, basis_2d)
        self.assertLess(alignment_1d, alignment_2d - 1e-6)
        self.assertAlmostEqual(alignment_2d, 1.0, places=6)

    def test_subspace_energy_is_negative_alignment(self):
        basis = build_refusal_subspace([np.array([1.0, 0.0])], k=1)
        h = np.array([1.0, 0.0])
        self.assertAlmostEqual(subspace_energy(h, basis), -1.0, places=6)

    def test_build_refusal_subspace_requires_input(self):
        with self.assertRaises(ValueError):
            build_refusal_subspace([], k=1)


class OrientedAxisTests(unittest.TestCase):
    def test_orient_basis_flips_toward_reference(self):
        basis = np.array([[-1.0, 0.0], [0.0, -1.0]])
        reference = np.array([1.0, 1.0])
        oriented = orient_basis(basis, reference)
        for row in oriented:
            self.assertGreaterEqual(np.dot(row, reference), 0.0)

    def test_orient_basis_is_a_no_op_when_already_aligned(self):
        basis = np.array([[1.0, 0.0]])
        reference = np.array([1.0, 0.5])
        oriented = orient_basis(basis, reference)
        np.testing.assert_allclose(oriented, basis)

    def test_signed_axis_projection_matches_cosine(self):
        h = np.array([1.0, 1.0])
        direction = np.array([1.0, 0.0])
        self.assertAlmostEqual(signed_axis_projection(h, direction), cosine(h, direction), places=6)

    def test_signed_axis_projection_can_be_negative(self):
        h = np.array([-1.0, 0.0])
        direction = np.array([1.0, 0.0])
        self.assertLess(signed_axis_projection(h, direction), 0.0)

    def test_residual_coupling_is_zero_for_one_dimensional_basis(self):
        basis = build_refusal_subspace([np.array([1.0, 0.0, 0.0])], k=1)
        self.assertEqual(residual_subspace_coupling(np.array([0.0, 1.0, 0.0]), basis), 0.0)

    def test_residual_coupling_is_nonzero_when_h_lies_in_second_dimension(self):
        diffs = [np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0])]
        basis = build_refusal_subspace(diffs, k=2)
        h = np.array([0.0, 0.0, 1.0]) + basis[1]
        self.assertGreater(residual_subspace_coupling(h, basis), 0.5)


if __name__ == "__main__":
    unittest.main()
