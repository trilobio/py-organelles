"""Pint integreation for units management.

:note: The ValueWithUnits class is copied directly from tcode-api.

:note: The operators defined on the ValueWithUnits class are a holdover from earlier, simpler times.

A future refactor will move this behavior more explicitly into domain models.
"""

from __future__ import annotations

from typing import Literal

from pint import Unit, UnitRegistry
from pint.errors import DimensionalityError
from pydantic import BaseModel

ureg: UnitRegistry = UnitRegistry()
Q_ = ureg.Quantity


class IncompatibleUnitsError(Exception):
    """Raised when an operation is attempted on two ValueWithUnits with incompatible units."""


class ValueWithUnits(BaseModel):
    """A numeric value with associated units.

    :note: The following values are all equivalent:

        ``ValueWithUnits(magnitude=0.005, units="L")``

        ``ValueWithUnits(magnitude=5, units="mL")``

        ``ValueWithUnits(magnitude=5000, units="uL")``

        ``ValueWithUnits(magnitude=5000, units="mm³")``

    :note: In the python implementation, ``pint`` is used to resolve units. see `tcode_api.units`.
    """

    type: Literal["ValueWithUnits"] = "ValueWithUnits"
    magnitude: float
    units: str

    def __hash__(self):
        # TODO (connor): Mia mentioned that this can produce collisions, fix.
        return hash(self.magnitude) ^ hash(self.units)

    def __str__(self) -> str:
        return f"{self.magnitude} {self.units}"

    def to(self, units: str | Unit) -> ValueWithUnits:
        """Convert to the specified units.

        :note: Units implementation in python uses `pint` under the hood.
        :param units: The units to convert to.

        """
        if units == self.units:
            return self.model_copy()
        if str(units) == self.units:
            return self.model_copy()
        pint_quantity = Q_(self.magnitude, self.units).to(units)
        return ValueWithUnits(magnitude=pint_quantity.magnitude, units=str(units))

    def __mul__(self, other: int | float) -> ValueWithUnits:
        """Multiply the ValueWithUnits by a scalar.

        :param other: The scalar to multiply by.

        :return: A new ValueWithUnits with a magnitude multiplied by the scalar.
        """
        try:
            other = float(other)
        except (TypeError, ValueError):
            return NotImplemented

        return ValueWithUnits(magnitude=self.magnitude * other, units=self.units)

    def __rmul__(self, other: int | float) -> ValueWithUnits:
        """Multiply the ValueWithUnits by a scalar.

        :param other: The scalar to multiply by.

        :return: A new ValueWithUnits with a magnitude multiplied by the scalar.
        """
        return self.__mul__(other)

    def __add__(self, other: object) -> ValueWithUnits:
        """Add two ValueWithUnits together, converting units as necessary.

        :note: the units of the returned ValueWithUnits will be the units of the left-hand side.

        :param other: The other ValueWithUnits to add.

        :return: A new ValueWithUnits representing the sum.

        :raises IncompatibleUnitsError: If the units are incompatible.
        """
        if not isinstance(other, ValueWithUnits):
            return NotImplemented

        if other.units == self.units:
            # This logic path is approx. 3x faster
            return ValueWithUnits(magnitude=self.magnitude + other.magnitude, units=self.units)

        try:
            pint_quantity = Q_(self.magnitude, self.units) + Q_(other.magnitude, other.units)
        except DimensionalityError as e:
            raise IncompatibleUnitsError(
                f"Cannot add quantities with incompatible units: "
                f"'{self.units}' and '{other.units}'"
            ) from e
        return ValueWithUnits(magnitude=pint_quantity.magnitude, units=str(pint_quantity.units))

    def __sub__(self, other: object) -> ValueWithUnits:
        """Subtract two ValueWithUnits, converting units as necessary.

        :note: the units of the returned ValueWithUnits will be the units of the left-hand side.

        :param other: The other ValueWithUnits to subtract.

        :return: A new ValueWithUnits representing the difference.

        :raises IncompatibleUnitsError: If the units are incompatible.
        """
        if not isinstance(other, ValueWithUnits):
            return NotImplemented

        if other.units == self.units:
            # This logic path is approx. 3x faster
            return ValueWithUnits(magnitude=self.magnitude - other.magnitude, units=self.units)

        try:
            pint_quantity = Q_(self.magnitude, self.units) - Q_(other.magnitude, other.units)
        except DimensionalityError as e:
            raise IncompatibleUnitsError(
                f"Cannot subtract quantities with incompatible units: "
                f"'{self.units}' and '{other.units}'"
            ) from e
        return ValueWithUnits(magnitude=pint_quantity.magnitude, units=str(pint_quantity.units))

    def __eq__(self, other: object) -> bool:
        """Check equality between two ValueWithUnits, converting units as necessary.

        :param other: The other ValueWithUnits to compare.

        :return: True if the two ValueWithUnits are equal, False otherwise.

        :raises IncompatibleUnitsError: If the units are incompatible.
        """
        if not isinstance(other, ValueWithUnits):
            return NotImplemented

        if other.units == self.units:
            return self.magnitude == other.magnitude
        self_q = Q_(self.magnitude, self.units)

        # Pint pythonically allows equality checks between incompatible units, but we can't
        # come up with a beneficial scenario for this behavior in TCode, so we raise an error.
        if not self_q.check(other.units):
            raise IncompatibleUnitsError(
                f"Cannot compare quantities with incompatible units: "
                f"'{self.units}' and '{other.units}'"
            )

        return self_q == Q_(other.magnitude, other.units)

    def __neg__(self) -> ValueWithUnits:
        """Negate the ValueWithUnits.

        :return: A new ValueWithUnits with a negated magnitude
        """
        return ValueWithUnits(magnitude=-self.magnitude, units=self.units)

    def __lt__(self, other: object) -> bool:
        """Check if this ValueWithUnits is less than another, converting units as necessary.

        :param other: The other ValueWithUnits to compare.

        :return: True if this ValueWithUnits is less than the other, False otherwise.

        :raises IncompatibleUnitsError: If the units are incompatible.
        """
        if not isinstance(other, ValueWithUnits):
            return NotImplemented

        if other.units == self.units:
            return self.magnitude < other.magnitude

        try:
            return Q_(self.magnitude, self.units) < Q_(other.magnitude, other.units)
        except DimensionalityError:
            raise IncompatibleUnitsError(
                f"Cannot compare quantities with incompatible units: "
                f"'{self.units}' and '{other.units}'"
            )

    def __le__(self, other: object) -> bool:
        """Check if this ValueWithUnits is less than or equal to another, converting units as necessary.

        :param other: The other ValueWithUnits to compare.

        :return: True if this ValueWithUnits is less than or equal to the other, False otherwise.

        :raises IncompatibleUnitsError: If the units are incompatible.
        """
        if not isinstance(other, ValueWithUnits):
            return NotImplemented

        if other.units == self.units:
            return self.magnitude <= other.magnitude

        try:
            return Q_(self.magnitude, self.units) <= Q_(other.magnitude, other.units)
        except DimensionalityError:
            raise IncompatibleUnitsError(
                f"Cannot compare quantities with incompatible units: "
                f"'{self.units}' and '{other.units}'"
            )

    def __gt__(self, other: object) -> bool:
        """Check if this ValueWithUnits is greater than another, converting units as necessary.

        :param other: The other ValueWithUnits to compare.

        :return: True if this ValueWithUnits is greater than the other, False otherwise.

        :raises IncompatibleUnitsError: If the units are incompatible.
        """
        if not isinstance(other, ValueWithUnits):
            return NotImplemented

        if other.units == self.units:
            return self.magnitude > other.magnitude

        try:
            return Q_(self.magnitude, self.units) > Q_(other.magnitude, other.units)
        except DimensionalityError:
            raise IncompatibleUnitsError(
                f"Cannot compare quantities with incompatible units: "
                f"'{self.units}' and '{other.units}'"
            )

    def __ge__(self, other: object) -> bool:
        """Check if this ValueWithUnits is greater than or equal to another, converting units as necessary.

        :param other: The other ValueWithUnits to compare.

        :return: True if this ValueWithUnits is greater than or equal to the other, False otherwise.

        :raises IncompatibleUnitsError: If the units are incompatible.
        """
        if not isinstance(other, ValueWithUnits):
            return NotImplemented

        if other.units == self.units:
            return self.magnitude >= other.magnitude

        try:
            return Q_(self.magnitude, self.units) >= Q_(other.magnitude, other.units)
        except DimensionalityError:
            raise IncompatibleUnitsError(
                f"Cannot compare quantities with incompatible units: "
                f"'{self.units}' and '{other.units}'"
            )
