"""Base data structure for PCB serial numbers.

I know, this file holds implementation-specific piece of code that is stored at rather too high of a level.
This decision was made to avoid the following circular dependency between `config-tools` and `firmware-tools`:
    - `config-tools` imports SerialNumber from `firmware-tools`
    - `firmware-tools` imports various tooling from `config-tools` in order to read .toml files
"""

from __future__ import annotations

import ctypes
import enum
import logging
import re
import struct
from typing import NamedTuple, Self

_logger = logging.getLogger(__name__)


def _byte_length(i: int) -> int:
    """Calculate minimum bytecount required to represent integer value."""
    return (i.bit_length() + 7) // 8


class ProductType(enum.IntEnum):
    trilobot = 1
    j1_and_j2_pcb = 2
    j3_or_j4_pcb = 3
    tool_pcb = 4
    fts_pcb = 5


class Factory(enum.IntEnum):
    office = 0
    pcbway = 1


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
    index: int  # TODO (mia): Fix the mypy [assignment] error here

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
    def from_int(cls, sn: int) -> Self:
        # struct.unpack is for nerds
        return cls._make(
            reversed(
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
        m = re.fullmatch(
            "T([0-9A-F]{4})"
            "V([0-9A-F]{2})([0-9A-F]{2})"
            "F([0-9A-F]{2})"
            "L([0-9A-F]{2})"
            "N([0-9A-F]{4})",
            s,
        )

        if m is None:
            raise ValueError(f"{s} is not a valid serial number")

        return cls._make(map(lambda v: int(v, 16), m.groups()))

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
