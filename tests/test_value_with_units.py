"""Unittests for tcode_api.api.core submodule."""

import unittest
from dataclasses import dataclass
from typing import Literal

# Using the below import style because it's how we expect users to import tcode_api
from py_organelles import UnitsError, ValueWithUnits
from py_organelles.core.units import Q_


class TestValueWithUnits(unittest.TestCase):
    """Unittests for :class:``ValueWithUnits``."""

    def _are_units_equivalent(self, units_a: str, units_b: str) -> bool:
        """Check if two unit strings are equivalent.

        :note: pint sometimes represents units differently but equivalently,
               e.g., "mm" vs "millimeter". We use pint to check equivalence.
        """
        return Q_(1, units_a) == Q_(1, units_b)

    def test_operate_on_incompatible_units(self) -> None:
        """Trying to perform any operations on ValueWithUnits with incompatible units should raise UnitsError.

        :note: For each test, we use magnitudes that would make the test pass, if not for the units.
            ex. 0 kg != 0 m, but both have magnitude 0.
        """
        v1 = ValueWithUnits(magnitude=0, units="kg")
        v2 = ValueWithUnits(magnitude=0, units="m")
        with self.subTest(name="addition"), self.assertRaises(UnitsError):
            _ = v1 + v2

        with self.subTest(name="subtraction"), self.assertRaises(UnitsError):
            _ = v1 - v2

        with self.subTest(name="equality"), self.assertRaises(UnitsError):
            v1 == v2

        with self.subTest(name="less than or equal"), self.assertRaises(UnitsError):
            v1 <= v2

        with self.subTest(name="greater than or equal"), self.assertRaises(UnitsError):
            v1 >= v2

        v1 = ValueWithUnits(magnitude=1, units="kg")
        with self.subTest(name="greater than"), self.assertRaises(UnitsError):
            v1 > v2

        v1 = ValueWithUnits(magnitude=-1, units="kg")
        with self.subTest(name="less than"), self.assertRaises(UnitsError):
            v1 < v2

    @dataclass
    class AdditiveOperationTest:
        """Inputs and expected outputs for unittesting ValueWithUnits additive operations."""

        a_magnitude: float | int
        a_units: str
        b_magnitude: float | int
        b_units: str
        operation: Literal["add", "subtract"]
        expected_magnitude: float | int
        expected_units: str

    def test_additive_compatible_units(self) -> None:
        """Test additive operations on ValueWithUnits with identical and compatible units."""
        tests = [
            # Addition, identical units
            self.AdditiveOperationTest(5, "mm", 10, "mm", "add", 15.0, "mm"),
            self.AdditiveOperationTest(5, "mm", -10, "mm", "add", -5.0, "mm"),
            self.AdditiveOperationTest(3.5, "kg", 2.5, "kg", "add", 6.0, "kg"),
            self.AdditiveOperationTest(0.000001, "m", 0.001, "m", "add", 0.001001, "m"),
            # Subtraction, identical units
            self.AdditiveOperationTest(10, "mm", 5, "mm", "subtract", 5, "mm"),
            self.AdditiveOperationTest(3.5, "kg", 2.5, "kg", "subtract", 1.0, "kg"),
            self.AdditiveOperationTest(0.001, "m", 0.0001, "m", "subtract", 0.0009, "m"),
            # Addition, compatible units
            self.AdditiveOperationTest(0.005, "m", 10, "mm", "add", 0.015, "m"),
            self.AdditiveOperationTest(5, "mm", 0.01, "m", "add", 15, "mm"),
            # Subtraction, compatible units
            self.AdditiveOperationTest(0.005, "m", -10, "mm", "subtract", 0.015, "m"),
            self.AdditiveOperationTest(5, "mm", -0.01, "m", "subtract", 15, "mm"),
        ]
        for i, test in enumerate(tests):
            with self.subTest(i=i, test=test):
                v1 = ValueWithUnits(magnitude=test.a_magnitude, units=test.a_units)
                v2 = ValueWithUnits(magnitude=test.b_magnitude, units=test.b_units)

                if test.operation == "add":
                    result = v1 + v2
                elif test.operation == "subtract":
                    result = v1 - v2
                else:
                    self.fail(f"Unsupported operation: {test.operation}")

                self.assertIsNot(result, v1)
                self.assertIsNot(result, v2)
                self.assertEqual(result.magnitude, test.expected_magnitude)
                self.assertTrue(
                    self._are_units_equivalent(result.units, test.expected_units),
                    msg=f"Expected units: {test.expected_units}, got: {result.units}",
                )

    @dataclass
    class ComparisonOperationTest:
        """Inputs and expected outputs for unittesting ValueWithUnits comparison operations."""

        a_magnitude: float | int
        a_units: str
        b_magnitude: float | int
        b_units: str
        expected_le: bool
        expected_lt: bool
        expected_ge: bool
        expected_gt: bool
        expected_eq: bool
        expected_ne: bool

        def __init__(
            self,
            a_mag: float | int,
            a_unt: str,
            b_mag: float | int,
            b_unt: str,
            le: bool,
            lt: bool,
            ge: bool,
            gt: bool,
            eq: bool,
            ne: bool,
        ) -> None:
            """Custom __init__ to enable shorter kwarg names, which in turn makes blocks of
            test definitions easier to read."""
            self.a_magnitude = a_mag
            self.a_units = a_unt
            self.b_magnitude = b_mag
            self.b_units = b_unt
            self.expected_le = le
            self.expected_lt = lt
            self.expected_ge = ge
            self.expected_gt = gt
            self.expected_eq = eq
            self.expected_ne = ne

    def test_comparisons(self) -> None:
        """Test comparison operations on ValueWithUnits with both identical and compatible units."""
        tests = [
            # Identical units
            self.ComparisonOperationTest(
                5, "mm", 10, "mm", eq=False, ne=True, lt=True, le=True, gt=False, ge=False
            ),
            self.ComparisonOperationTest(
                10, "mm", 5, "mm", eq=False, ne=True, lt=False, le=False, gt=True, ge=True
            ),
            self.ComparisonOperationTest(
                5, "mm", 5, "mm", eq=True, ne=False, lt=False, le=True, gt=False, ge=True
            ),
            # Compatible units
            self.ComparisonOperationTest(
                0.005, "m", 10, "mm", eq=False, ne=True, lt=True, le=True, gt=False, ge=False
            ),
            self.ComparisonOperationTest(
                10, "mm", 0.005, "m", eq=False, ne=True, lt=False, le=False, gt=True, ge=True
            ),
            self.ComparisonOperationTest(
                0.01, "m", 5, "mm", eq=False, ne=True, lt=False, le=False, gt=True, ge=True
            ),
            self.ComparisonOperationTest(
                5, "mm", 0.01, "m", eq=False, ne=True, lt=True, le=True, gt=False, ge=False
            ),
            self.ComparisonOperationTest(
                0.01, "m", 10, "mm", eq=True, ne=False, lt=False, le=True, gt=False, ge=True
            ),
        ]
        for i, test in enumerate(tests):
            with self.subTest(i=i, test=test):
                v1 = ValueWithUnits(magnitude=test.a_magnitude, units=test.a_units)
                v2 = ValueWithUnits(magnitude=test.b_magnitude, units=test.b_units)

                self.assertEqual(v1 <= v2, test.expected_le)
                self.assertEqual(v1 < v2, test.expected_lt)
                self.assertEqual(v1 >= v2, test.expected_ge)
                self.assertEqual(v1 > v2, test.expected_gt)
                self.assertEqual(v1 == v2, test.expected_eq)
                self.assertEqual(v1 != v2, test.expected_ne)

    @dataclass
    class MultiplicationTest:
        """Inputs and expected outputs for unittesting ValueWithUnits * scalar multiplication."""

        v_magnitude: float | int
        v_units: str
        scalar: float | int
        expected_magnitude: float | int
        expected_units: str

    def test_multiplication(self) -> None:
        """Test multiplication of ValueWithUnits by scalars."""
        tests = [
            self.MultiplicationTest(5, "mm", 2, 10, "mm"),
            self.MultiplicationTest(3.5, "kg", 3, 10.5, "kg"),
            self.MultiplicationTest(0.001, "m", 1000, 1, "m"),
            self.MultiplicationTest(10, "N", -1, -10, "N"),
            self.MultiplicationTest(2.5, "m/s", 0, 0, "m/s"),
            self.MultiplicationTest(7, "ul", 0.5, 3.5, "ul"),
        ]

        for i, test in enumerate(tests):
            with self.subTest(i=i, test=test):
                v = ValueWithUnits(magnitude=test.v_magnitude, units=test.v_units)

                mul_result = test.scalar * v
                rmul_result = v * test.scalar
                self.assertEqual(mul_result, rmul_result)
                self.assertIsNot(mul_result, v)
                self.assertEqual(mul_result.magnitude, test.expected_magnitude)
                self.assertTrue(
                    self._are_units_equivalent(mul_result.units, test.expected_units),
                    msg=f"Expected units: {test.expected_units}, got: {mul_result.units}",
                )
