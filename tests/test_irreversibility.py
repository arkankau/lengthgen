from __future__ import annotations

import unittest

import numpy as np

from thermosafety.irreversibility import (
    antisymmetric_fraction,
    common_pca_basis,
    depth_irreversibility_profile,
)


class IrreversibilityEstimatorTests(unittest.TestCase):
    def test_reversible_symmetric_coupling_gives_near_zero(self):
        # Y = a*X + noise with X,Y from a symmetric relation -> lagged cross-cov symmetric.
        rng = np.random.default_rng(0)
        n, k = 4000, 5
        X = rng.normal(size=(n, k))
        Y = 0.8 * X + 0.3 * rng.normal(size=(n, k))  # diagonal (symmetric) coupling
        self.assertLess(antisymmetric_fraction(X, Y), 0.02)

    def test_irreversible_rotational_coupling_gives_positive(self):
        # A rotational (non-normal, antisymmetric) coupling makes the cross-cov asymmetric.
        rng = np.random.default_rng(1)
        n, k = 4000, 4
        X = rng.normal(size=(n, k))
        R = np.eye(k) * 0.6
        R[0, 1] = 0.7
        R[1, 0] = -0.7  # antisymmetric off-diagonal -> irreversible
        Y = X @ R.T + 0.1 * rng.normal(size=(n, k))
        self.assertGreater(antisymmetric_fraction(X, Y), 0.05)

    def test_irreversible_exceeds_reversible(self):
        rng = np.random.default_rng(2)
        n, k = 4000, 4
        X = rng.normal(size=(n, k))
        Y_rev = 0.7 * X + 0.2 * rng.normal(size=(n, k))
        R = np.eye(k) * 0.5
        R[0, 1], R[1, 0] = 0.6, -0.6
        Y_irr = X @ R.T + 0.1 * rng.normal(size=(n, k))
        self.assertGreater(antisymmetric_fraction(X, Y_irr), antisymmetric_fraction(X, Y_rev))

    def test_common_pca_basis_shape(self):
        rng = np.random.default_rng(3)
        H = rng.normal(size=(500, 16))
        basis = common_pca_basis(H, k=6)
        self.assertEqual(basis.shape, (6, 16))
        # rows approximately orthonormal
        gram = basis @ basis.T
        np.testing.assert_allclose(gram, np.eye(6), atol=1e-6)

    def test_profile_shapes(self):
        rng = np.random.default_rng(4)
        traj = rng.normal(size=(300, 8, 12))  # 300 tokens, 8 layers, dim 12
        prof = depth_irreversibility_profile(traj, k=5)
        self.assertEqual(prof["irr_fraction"].shape, (7,))
        self.assertEqual(prof["repr_change"].shape, (7,))

    def test_synthetic_arrow_trajectory_is_irreversible(self):
        # Build trajectories with a consistent rotational drift across depth -> real arrow of time.
        rng = np.random.default_rng(5)
        n, L, d = 2000, 8, 6
        R = np.eye(d) * 0.9
        R[0, 1], R[1, 0] = 0.4, -0.4
        traj = np.zeros((n, L, d))
        traj[:, 0, :] = rng.normal(size=(n, d))
        for l in range(1, L):
            traj[:, l, :] = traj[:, l - 1, :] @ R.T + 0.05 * rng.normal(size=(n, d))
        prof = depth_irreversibility_profile(traj, k=d)
        self.assertGreater(prof["irr_fraction"].mean(), 0.05)


if __name__ == "__main__":
    unittest.main()
