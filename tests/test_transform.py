import random
import unittest

import numpy as np
from scipy.spatial.transform import Rotation

from py_organelles.core.transform import (
    euler_angles_from_rotation_matrix,
    rotation_from_euler_angles,
)

seq = "zyx"  # Implies extrinsic rotation
degrees = False
random.seed(0)
np.set_printoptions(suppress=True, precision=6)


def _randangle() -> float:
    """Generate a random angle in the range [-2pi, 2pi]."""
    return random.uniform(-2 * np.pi, 2 * np.pi)


# Ensure at least one test of each combination containing a zero angle
angles_to_test: list[tuple[float, float, float]] = [
    (0.0, 0.0, 0.0),
    (_randangle(), 0.0, 0.0),
    (0.0, _randangle(), 0.0),
    (0.0, 0.0, _randangle()),
    (_randangle(), _randangle(), 0.0),
    (_randangle(), 0.0, _randangle()),
    (0.0, _randangle(), _randangle()),
]
# Perform several more random tests with non-zero angles
for _ in range(10 - len(angles_to_test)):
    angles_to_test.append((_randangle(), _randangle(), _randangle()))


class TestRotationFromEulerAngles(unittest.TestCase):
    def test_rotation_from_euler_angles(self):
        """Test rotation_from_euler_angles against scipy.spatial.transform.Rotation.from_euler."""
        for i, angles in enumerate(angles_to_test):
            with self.subTest(i=i, angles=angles):
                scipy_ans = Rotation.from_euler(seq=seq, angles=angles, degrees=degrees).as_matrix()
                local_ans = rotation_from_euler_angles(*angles)
                self.assertTrue(
                    np.allclose(scipy_ans, local_ans, atol=1e-6),
                    msg=f"\nScipy:\n{scipy_ans}\nLocal:\n{local_ans}",
                )


class TestEulerAnglesFromRotationMatrix(unittest.TestCase):
    def test_euler_angles_from_rotation_matrix(self):
        """Test euler_angles_from_rotation_matrix against scipy.spatial.transform.Rotation.as_euler."""

        for i, angles in enumerate(angles_to_test):
            with self.subTest(i=i, angles=angles):
                mat = Rotation.from_euler(seq=seq, angles=angles, degrees=degrees).as_matrix()
                local_eul = euler_angles_from_rotation_matrix(mat)
                local_ans = Rotation.from_euler(
                    seq=seq, angles=local_eul, degrees=degrees
                ).as_matrix()
                self.assertTrue(
                    np.allclose(mat, local_ans, atol=1e-6),
                    msg=f"\nScipy:\n{mat}\nLocal:\n{local_ans}",
                )
