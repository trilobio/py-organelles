"""Base data structure for PCB serial numbers.

I know, this file holds implementation-specific piece of code that is stored at rather too high of a level.
This decision was made to avoid the following circular dependency between `config-tools` and `firmware-tools`:
    - `config-tools` imports SerialNumber from `firmware-tools`
    - `firmware-tools` imports various tooling from `config-tools` in order to read .toml files
"""
from __future__ import annotations

import logging

_logger_name = "core.serial_number"
_logger = logging.getLogger(_logger_name)


def _byte_length(i: int) -> int:
    """Calculate minimum bytecount required to represent integer value."""
    return (i.bit_length() + 7) // 8


class SerialNumber:
    """Python representation of PCB serial number,
    contains methods for converting to and from bytes."""

    _byteorder = "big"  # Lol, whoops

    def __init__(self, pcb_id: int, version_id: int, instance_id: int):
        """Create SerialNumber instance."""
        if any([not isinstance(i, int) for i in (pcb_id, version_id, instance_id)]):
            raise TypeError("SerialNumber args must all be integers")

        if pcb_id < 0 or _byte_length(pcb_id) > 2:
            raise ValueError(f"pcb_id must be positive & fit in 2 bytes, got {pcb_id}")
        if pcb_id == 0:
            _logger.warning("SerialNumbers with a PCB ID of 0 are reserved for testing")
        self.pcb_id = pcb_id

        if version_id < 0 or _byte_length(version_id) > 1:
            raise ValueError(f"version_id must be positive & fit in 1 byte, got {version_id}")
        if version_id == 0:
            _logger.warning("SerialNumbers with a Version ID of 0 are reserved for testing")
        self.version_id = version_id

        if instance_id < 0 or _byte_length(instance_id) > 4:
            raise ValueError(f"instance_id must be positive & fit in 4 bytes, got {instance_id}")
        if instance_id == 0:
            _logger.warning("SerialNumbers with an Instance ID of 0 are reserved for testing")
        self.instance_id = instance_id

    @classmethod
    def from_bytes(cls, data: bytes) -> SerialNumber:
        """Create SerialNumber instance from bytes."""
        if not len(data) == 7:
            raise ValueError(f"SerialNumber must be 7 bytes long, got {len(data)}")

        pcb_id = int.from_bytes(data[0:2], byteorder=cls._byteorder, signed=False)
        version_id = data[2]
        instance_id = int.from_bytes(data[3:], byteorder=cls._byteorder, signed=False)
        return cls(pcb_id, version_id, instance_id)

    @classmethod
    def from_str(cls, data: str) -> SerialNumber:
        """Create SerialNumber instance from string.

        Formats accepted:
            * 1-1-1
            * 001-v1-000001
        """
        components = data.split("-")
        if not len(components) == 3:
            raise ValueError(
                f"SerialNumber must contain 3 '-'-separated components, got {len(components)}"
            )

        pcb_id = int(components[0])
        if components[1][0] == "v":
            version_id = int(components[1][1:])
        else:
            version_id = int(components[1])

        instance_id = int(components[2])
        return cls(pcb_id, version_id, instance_id)

    def to_bytes(self) -> bytes:
        """Represent SerialNumber in bytes."""
        pcb_id_bytes = (self.pcb_id).to_bytes(length=2, byteorder=self._byteorder)
        version_id_bytes = (self.version_id).to_bytes(length=1, byteorder=self._byteorder)
        instance_id_bytes = (self.instance_id).to_bytes(length=4, byteorder=self._byteorder)
        return pcb_id_bytes + version_id_bytes + instance_id_bytes

    def __str__(self) -> str:
        """Represent SerialNumber as string."""
        pcb_id_len = len(str(self.pcb_id))
        instance_id_len = len(str(self.instance_id))
        return (
            f"{'0' * (3 - pcb_id_len)}{self.pcb_id}-"
            f"v{self.version_id}-"
            f"{'0' * (5 - instance_id_len)}{self.instance_id}"
        )

    def __repr__(self) -> str:
        return f"SerialNumber(pcb_id={self.pcb_id}, version_id={self.version_id}, instance_id={self.instance_id})"

    def __eq__(self, other: SerialNumber) -> bool:
        """Compare SerialNumber instances for equality."""
        return (
            self.pcb_id == other.pcb_id
            and self.version_id == other.version_id
            and self.instance_id == other.instance_id
        )
