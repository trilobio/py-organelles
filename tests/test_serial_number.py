"""Unittests for serial_number.py"""

import unittest

from core.serial_number import SerialNumber


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

    def test_from_bytes(self) -> None:
        """Test SerialNumber constructor from_bytes."""
        # Too few bytes given
        with self.assertRaises(ValueError):
            SerialNumber.from_bytes(b"\x00\x01\x02\x03\x04")

        # Too many bytes given
        with self.assertRaises(ValueError):
            SerialNumber.from_bytes(b"\x00\x01\x02\x03\x04\x05\x06\x07\x00")

        b = b"\x00\x01\x02\x00\x00\x00\x0a\x00"
        SerialNumber.from_bytes(b)

    def test_to_bytes(self) -> None:
        """Test SerialNumber.to_bytes method."""
        b = b"\xf4\xa1\x62\xd0\x91\x00\x0a\x00"
        sn = SerialNumber.from_bytes(b)
        self.assertEqual(b, sn.to_bytes())


if __name__ == "__main__":
    unittest.main()
