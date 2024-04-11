"""Base classes for dataclasses and enumerations."""
from __future__ import annotations

import enum

from typing_extensions import Self


class Base:
    """Base class for dataclass.dataclasses."""

    def __post_init__(self):
        """An empty __post_init__ method to implement co-operative inheritance for dataclasses"""
        if hasattr(super(), "__post_init__"):
            raise RuntimeError("Base must be the final Class in __post_init__ MRO")


class KindBase(enum.Enum):
    """Base class for Kind enumerations of objects:

    Example.
        ```
        @enum.unique
        class Kind(KindBase):
            KIND_A = enum.auto()
            KIND_B = enum.auto()
        ```
    """

    @classmethod
    def from_str(cls, raw: str) -> Self:
        """Return KindBase subclass entry corresponding to string.

        Handles case-insensitivity and underscores; assumes subclass is enum.Enum.
        """
        raw = raw.upper()
        raw = raw[1:] if raw[0] == "_" else raw
        try:
            return cls[raw]

        except KeyError as err:
            raise KeyError(f"{cls.__name__} has no entry {raw}") from err
