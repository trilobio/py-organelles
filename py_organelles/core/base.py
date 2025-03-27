"""Base classes for dataclasses and enumerations."""

import enum
from typing import Protocol, Self


class Base:
    """Base class for dataclass.dataclasses."""

    def __post_init__(self):
        """An empty __post_init__ method to implement co-operative inheritance for dataclasses"""
        if hasattr(super(), "__post_init__"):
            raise RuntimeError("Base must be the final Class in __post_init__ MRO")


class KindInterface(Protocol):
    """Standard interface for a Kind class."""

    @classmethod
    def from_str(cls, raw: str) -> Self:
        raise NotImplementedError

    def to_str(self) -> str:
        raise NotImplementedError


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

    def to_str(self) -> str:
        """Return string representation of KindBase subclass entry.

        :return: uppercase string representation of KindBase subclass entry
        :rtype: str
        """
        return self.name.upper()
