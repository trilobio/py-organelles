"""Unittests for serial_number.py"""

import logging
import unittest

from core.serial_number import PCBSerialNumber, SerialNumber


class TestSerialNumber(unittest.TestCase):
    def test_serial_from_string(self):
        sn = SerialNumber.from_str("T0001V0103F00L00N000B")
        self.assertEqual(sn.index, 11)
        self.assertEqual(sn.factory, 0)
        self.assertEqual(sn.line, 0)
        self.assertEqual(sn.version_minor, 3)
        self.assertEqual(sn.version_major, 1)
        self.assertEqual(sn.product_type, 1)

    def test_serial_to_string(self):
        sn = SerialNumber(1, 1, 3, 0, 0, 11)
        self.assertEqual(str(sn), "T0001V0103F00L00N000B")

    def test_serial_to_int(self):
        sn = SerialNumber(1, 1, 3, 0, 0, 11)
        self.assertEqual(int(sn), 0x101030000000B)

    def test_int_to_serial(self):
        sn = SerialNumber.from_int(0x101030001000F)
        self.assertEqual(sn.index, 15)
        self.assertEqual(sn.factory, 0)
        self.assertEqual(sn.line, 1)
        self.assertEqual(sn.version_minor, 3)
        self.assertEqual(sn.version_major, 1)
        self.assertEqual(sn.product_type, 1)


class TestPCBSerialNumber(unittest.TestCase):
    """SerialNumber unittests."""

    def test_from_bytes(self) -> None:
        """Test SerialNumber constructor from_bytes."""
        # Too few bytes given
        with self.assertRaises(ValueError):
            PCBSerialNumber.from_bytes(b"\x00\x01\x02\x03\x04")

        # Too many bytes given
        with self.assertRaises(ValueError):
            PCBSerialNumber.from_bytes(b"\x00\x01\x02\x03\x04\x05\x06\x07")

        b = b"\x00\x01\x02\x00\x00\x00\x0A"
        sn = PCBSerialNumber.from_bytes(b)
        self.assertEqual(sn.version_id, 2)
        self.assertEqual(sn.instance_id, 10)
        self.assertEqual(sn.pcb_id, 1)

    def test_to_bytes(self) -> None:
        """Test SerialNumber.to_bytes method."""
        b = b"\xF4\xA1\x62\xD0\x91\x00\x0A"
        sn = PCBSerialNumber.from_bytes(b)
        self.assertEqual(b, sn.to_bytes())

    def test_from_str(self) -> None:
        """Test SerialNumber constructor from_str."""
        # Not a string
        with self.subTest(value=b"1-v1-1"):
            with self.assertRaises(TypeError):
                PCBSerialNumber.from_str(b"1-v1-1")

        # Too many separators
        with self.subTest(value="0-0-0-0"):
            with self.assertRaises(ValueError):
                PCBSerialNumber.from_str("0-0-0-0")

        # Bad separator given
        with self.subTest(value="0.v0.0"):
            with self.assertRaises(ValueError):
                PCBSerialNumber.from_str("0.v0.0")

        # Invalid pcb_id
        with self.subTest(value="one-v1-1"):
            with self.assertRaises(ValueError):
                PCBSerialNumber.from_str("one-v1-1")

        # Invalid version
        with self.subTest(value="1-version1-1"):
            with self.assertRaises(ValueError):
                PCBSerialNumber.from_str("1-version1-1")

        # Invalid instance_id
        with self.subTest(value="1-v1-one"):
            with self.assertRaises(ValueError):
                PCBSerialNumber.from_str("1-v1-one")

        # Test a couple valid strings
        self.assertEqual(PCBSerialNumber(1, 1, 1), PCBSerialNumber.from_str("1-1-1"))
        self.assertEqual(PCBSerialNumber(1, 1, 1), PCBSerialNumber.from_str("001-v1-00001"))

    def test_to_str(self) -> None:
        """Test SerialNumber.to_str method."""
        # Suppress logging warning about zeros
        logging.getLogger("core.serial_number").setLevel(logging.ERROR)
        test_cases = [
            PCBSerialNumber(1, 1, 1),
            PCBSerialNumber(23, 0, 256),
        ]
        for sn in test_cases:
            with self.subTest(sn=sn):
                self.assertEqual(sn, PCBSerialNumber.from_str(str(sn)))

    def test_init(self) -> None:
        """Test SerialNumber __init__ constructor arg checking."""
        with self.subTest(msg="pcb_id not an int", pcb_id="1"):
            with self.assertRaises(TypeError):
                PCBSerialNumber("1", 1, 1)

        with self.subTest(msg="version_id not an int", version_id=1.0):
            with self.assertRaises(TypeError):
                PCBSerialNumber(1, 1.0, 1)

        with self.subTest(msg="instance_id not an int", instance_id=b"1"):
            with self.assertRaises(TypeError):
                PCBSerialNumber(1, 1, b"1")

        with self.subTest(msg="pcb_id too big", pcb_id=65536):
            with self.assertRaises(ValueError):
                PCBSerialNumber(65536, 1, 1)

        with self.subTest(msg="pcb_id too small", pcb_id=-1):
            with self.assertRaises(ValueError):
                PCBSerialNumber(-1, 1, 1)

        with self.subTest(msg="version_id too big", version_id=256):
            with self.assertRaises(ValueError):
                PCBSerialNumber(1, 256, 1)

        with self.subTest(msg="version_id too small", version_id=-1):
            with self.assertRaises(ValueError):
                PCBSerialNumber(1, -1, 1)

        with self.subTest(msg="instance_id too big", instance_id=4294967296):
            with self.assertRaises(ValueError):
                PCBSerialNumber(1, 1, 4294967296)

        with self.subTest(msg="instance_id too small", instance_id=-1):
            with self.assertRaises(ValueError):
                PCBSerialNumber(1, 1, -1)


if __name__ == "__main__":
    unittest.main()
