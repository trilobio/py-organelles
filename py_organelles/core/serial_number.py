"""Base data structure for serial numbers.

I know, this file holds implementation-specific piece of code that is stored at rather too high of a level.
This decision was made to avoid the following circular dependency between `config-tools` and `firmware-tools`:
    - `config-tools` imports SerialNumber from `firmware-tools`
    - `firmware-tools` imports various tooling from `config-tools` in order to read .toml files
"""

import ctypes
import enum
import itertools
import re
import struct
from collections.abc import Iterator
from typing import Iterable, NamedTuple, Self

#: A serial number, canonical or shortened. Every field accepts anything from one digit up
#: to its full width, so `T0001V0106F00L00N000B` and `T1V106F0L0NB` both read
_SERIAL_NUMBER_PATTERN = re.compile(
    "T([0-9A-F]{1,4})V([0-9A-F]{1,4})F([0-9A-F]{1,2})L([0-9A-F]{1,2})N([0-9A-F]{1,4})"
)


def _byte_length(i: int) -> int:
    """Calculate minimum bytecount required to represent integer value."""
    return (i.bit_length() + 7) // 8


class ProductType(enum.IntEnum):
    trilobot = 1
    j1_and_j2_pcb = 2
    j3_or_j4_pcb = 3
    tool_pcb = 4
    fts_pcb = 5
    frame = 6


class Factory(enum.IntEnum):
    office = 0
    pcbway = 1

    #: Placeholder value to use in unit testing - makes it clear if a test value leaks into
    #: production.
    unittest = 255


_serial_number_struct_format_str: str = "<Q"  # little-endian unsigned long long


class SerialNumber(NamedTuple):
    """
    Simple implementation of serial number standard defined in
    https://docs.google.com/document/d/1s6pC0wdmqtIf6gs2tAd2PYZgk5VbTx11_sRjl1heAyU/edit
    """

    product_type: ProductType
    version_major: int
    version_minor: int
    factory: Factory
    line: int  # there is no enum for line because its meaning is factory-dependent
    index: int  # type: ignore [assignment]  # TODO (mia): Fix the mypy [assignment] error here

    def pack(self) -> int:
        # check for overflow
        c_defs = {
            "product_type": ctypes.c_uint16(self.product_type),
            "version_major": ctypes.c_uint8(self.version_major),
            "version_minor": ctypes.c_uint8(self.version_minor),
            "factory": ctypes.c_uint8(self.factory),
            "line": ctypes.c_uint8(self.line),
            "index": ctypes.c_uint16(self.index),
        }

        for field in self._fields:
            if c_defs[field].value != (n := getattr(self, field)):
                raise ValueError(f"{field} value of {n} overflowed")

        return (
            self.product_type << 48
            | self.version_major << 40
            | self.version_minor << 32
            | self.factory << 24
            | self.line << 16
            | self.index
        )

    def to_bytes(self) -> bytes:
        """Convert the serial number to a byte array."""
        return struct.pack(_serial_number_struct_format_str, self.pack())

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Convert a byte array to a serial number."""
        if len(data) != struct.calcsize(_serial_number_struct_format_str):
            raise ValueError(
                f"Invalid byte length: {len(data)}. Expected {struct.calcsize(_serial_number_struct_format_str)}"
            )
        return cls.from_int(struct.unpack(_serial_number_struct_format_str, data)[0])

    @classmethod
    def _build(
        cls,
        product_type: int,
        version_major: int,
        version_minor: int,
        factory: int,
        line: int,
        index: int,
    ) -> Self:
        """Assemble a serial number from the raw fields, converting the two enums.

        :param product_type: What the thing is.
        :param version_major: Hardware major version.
        :param version_minor: Hardware minor version.
        :param factory: Where it was made.
        :param line: Which line made it, meaning whatever that factory says it means.
        :param index: Which one it is.

        :raises ValueError: If *product_type* or *factory* names no member. Unknown
            hardware is a thing to add to the enum, not to carry as a bare number.

        :return: The serial number, with both enums as members.
        """
        return cls(
            product_type=ProductType(product_type),
            version_major=version_major,
            version_minor=version_minor,
            factory=Factory(factory),
            line=line,
            index=index,
        )

    @classmethod
    def from_int(cls, sn: int) -> Self:
        """Read a serial number out of its packed integer form.

        :param sn: The packed form, as `pack` produces it.

        :raises ValueError: If the product type or factory names no member.

        :return: The serial number.
        """
        # struct.unpack is for nerds
        return cls._build(
            *reversed(
                [
                    sn % 2**16,  # index
                    (r := sn >> 16) % 2**8,  # line
                    (r := r >> 8) % 2**8,  # factory
                    (r := r >> 8) % 2**8,  # minor
                    (r := r >> 8) % 2**8,  # major
                    r >> 8,  # type
                ]
            )
        )

    @classmethod
    def from_str(cls, s: str) -> Self:
        """Read a serial number out of its canonical string form.

        :param s: The string, as `__str__` produces it.

        :raises ValueError: If *s* is not a serial number at all, or if its product type
            or factory names no member.

        :return: The serial number.
        """
        m = _SERIAL_NUMBER_PATTERN.fullmatch(s)
        if m is None:
            raise ValueError(f"{s} is not a valid serial number")

        product_type, version, factory, line, index = (int(group, 16) for group in m.groups())

        return cls._build(
            product_type=product_type,
            # The version is one field when it is written down and two when it is read:
            # `V0106` is major 1, minor 6, and shortening it to `V106` drops a zero from
            # the pair rather than from either half - which is why it is split by
            # arithmetic on the whole field rather than by slicing the string.
            version_major=version >> 8,
            version_minor=version & 0xFF,
            factory=factory,
            line=line,
            index=index,
        )

    def __int__(self):
        return self.pack()

    def __str__(self):
        return (
            f"T{self.product_type:04X}"
            f"V{self.version_major:02X}{self.version_minor:02X}"
            f"F{self.factory:02X}"
            f"L{self.line:02X}"
            f"N{self.index:04X}"
        )


RawSerialNumberListInput = str | SerialNumber | Iterable[str | SerialNumber] | None


def sanitize_serial_number_input(raw_input: RawSerialNumberListInput) -> list[SerialNumber]:
    """Cleans and standardizes a list of serial numbers from various input formats.

    :param raw_input: Input serial numbers in various formats. Can be a single string, a
        SerialNumber object, a list of strings or SerialNumber objects, or None.

    :return: A list of standardized SerialNumber objects. If input is None, returns an empty list.
    :raises ExceptionGroup: If any inputs are invalid, raises an ExceptionGroup containing all
        encountered exceptions as ValueErrors or TypeErrors.
    """
    if raw_input is None:
        return []

    if isinstance(raw_input, (str, SerialNumber)):
        raw_input = [raw_input]

    try:
        iter(raw_input)
    except TypeError:
        # We could raise this TypeError directly, but wrapping it in a list means that the
        # error is instead raised as part of an ExceptionGroup below, which makes a more
        # consistent error interface.
        raw_input = [raw_input]  # type: ignore [list-item]

    exceptions: list[Exception] = []
    cleaned_serial_numbers: list[SerialNumber] = []
    for i, item in enumerate(raw_input):
        if isinstance(item, SerialNumber):
            cleaned_serial_numbers.append(item)
        elif isinstance(item, str):
            try:
                cleaned_serial_numbers.append(SerialNumber.from_str(item))
            except ValueError as ve:
                exceptions.append(ve)
        else:
            exceptions.append(
                TypeError(f"input {i} has invalid type {type(item)}; expected str or SerialNumber.")
            )

    if exceptions:
        raise ExceptionGroup("One or more serial number inputs were invalid.", exceptions)

    return cleaned_serial_numbers


#: Shared by every generator, so that two of them never hand out the same serial number.
_generated_indices = itertools.count(1)


def generate_serial_numbers(
    product_type: ProductType,
    version_major: int = 1,
    version_minor: int = 0,
    factory: Factory = Factory.unittest,
    line: int = 0,
) -> Iterator[SerialNumber]:
    """Yield serial numbers of a given kind, each one different from the last.

    For tests and mocks, which need serial numbers that are well-formed and tell each
    other apart but whose values mean nothing.

    The index comes from a counter shared by every generator in the process, so two
    generators - of the same product type or not - never collide, and a caller can take
    one more whenever it needs a serial number that is deliberately not among the others.

    :param product_type: What the generated serial numbers say they are.
    :param version_major: Hardware major version.
    :param version_minor: Hardware minor version.
    :param factory: Where the generated serial numbers say they were made. `unittest` by
        default, so one that escapes into somewhere real is recognisable as made up.
    :param line: Which line made them.

    :return: A stream of serial numbers differing only in index. The index is 16
        bits wide, so one process must not take more than 65535 of them.
    """
    for index in _generated_indices:
        yield SerialNumber(
            product_type=product_type,
            version_major=version_major,
            version_minor=version_minor,
            factory=factory,
            line=line,
            index=index,
        )
