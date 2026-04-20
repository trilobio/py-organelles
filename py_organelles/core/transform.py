"""Local dependency-less implementation of matrix <--> Euler angles conversions.

:note: specifically, these methods duplicate the behavior of the following functions:
* scipy.spatial.transform.Rotation.as_euler(seq="zyx", degrees=False)
* scipy.spatial.transform.Rotation.from_euler(seq="zyx", angles=[0.0, 1.0, 2.0], degrees=False)

The following document is useful to reference:
* https://www.geometrictools.com/Documentation/EulerAngles.pdf
* Ensure that you reference "2.1   Factor as RxRyRz", which due to matrix multiplication corresponds to the above
    order of rotations (z, y, x).
"""

import numpy as np

from .types import Matrix


def rotation_from_euler_angles(
    z_angle: float, y_angle: float = 0.0, x_angle: float = 0.0
) -> np.ndarray:
    """Convert Euler angles to a 3x3 rotation matrix.

    :param z_angle: rotation angle about the z-axis, in radians
    :param y_angle: rotation angle about the y-axis, in radians
    :param x_angle: rotation angle about the x-axis, in radians
    :returns: a 3x3 numpy array containing the resulting rotation matrix
    """
    cz, cy, cx = np.cos(z_angle), np.cos(y_angle), np.cos(x_angle)
    sz, sy, sx = np.sin(z_angle), np.sin(y_angle), np.sin(x_angle)
    return np.array(
        [
            [cy * cz, -cy * sz, sy],
            [cz * sx * sy + cx * sz, cx * cz - sx * sy * sz, -cy * sx],
            [-cx * cz * sy + sx * sz, cz * sx + cx * sy * sz, cx * cy],
        ]
    )


def transform_from_euler_angles(
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    a: float = 0.0,
    b: float = 0.0,
    c: float = 0.0,
) -> Matrix:
    """Convert a 3D transformation represented in xyzabc into a 4x4 transformation matrix.

    :param x: x-component of transform (m).
    :param y: y-component of transform (m).
    :param z: z-component of transform (m).
    :param a: extrinsic rotation about z-axis (rad).
    :param b: extrinsic rotation about y-axis (rad).
    :param c: extrinsic rotation about x-axis (rad).

    :returns: transformation matrix as a 4x4 numpy array
    """
    rmat = rotation_from_euler_angles(z_angle=a, y_angle=b, x_angle=c)
    return np.array(
        [
            [rmat[0, 0], rmat[0, 1], rmat[0, 2], x],
            [rmat[1, 0], rmat[1, 1], rmat[1, 2], y],
            [rmat[2, 0], rmat[2, 1], rmat[2, 2], z],
            [0, 0, 0, 1],
        ]
    ).tolist()


def euler_angles_from_rotation_matrix(mat: np.ndarray) -> np.ndarray:
    """Convert a 3x3 rotation matrix to Euler angles.

    :param matrix: a 3x3 numpy array containing the rotation matrix
    :returns: a numpy array containing the Euler angles (z, y, x) in radians
    """
    if mat[0, 2] < 1:
        if mat[0, 2] > -1:
            theta_y = np.arcsin(mat[0, 2])
            theta_x = np.arctan2(-mat[1, 2], mat[2, 2])
            theta_z = np.arctan2(-mat[0, 1], mat[0, 0])

        else:  # mat[0, 2] == -1
            # Not a unique solution: theta_z - theta_x = atan2(mat[1, 0], mat[1, 1])
            theta_y = -np.pi / 2
            theta_x = -np.arctan2(mat[1, 0], mat[1, 1])
            theta_z = 0.0

    else:  # mat[0, 2] = 1
        # Not a unique solution: theta_z + theta_x = atan2(mat[1, 0], mat[1, 1])
        theta_y = np.pi / 2
        theta_x = np.arctan2(mat[1, 0], mat[1, 1])
        theta_z = 0.0

    return np.array([theta_z, theta_y, theta_x])
