"""Unittests for serial_number.py"""

import unittest

from core.serial_number import SerialNumber, sanitize_serial_number_input


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


class TestSanitizeSerialNumberInput(unittest.TestCase):
    """Unittests for sanitize_serial_number_input function."""

    def test_none_input(self) -> None:
        """Test None input."""
        result = sanitize_serial_number_input(None)
        self.assertEqual(result, [])

    def test_single_string_input(self) -> None:
        """Test single string input."""
        result = sanitize_serial_number_input("T0001V0103F00L00N000B")
        self.assertEqual(result, [SerialNumber.from_str("T0001V0103F00L00N000B")])

    def test_single_serial_number_input(self) -> None:
        """Test single SerialNumber input."""
        sn = SerialNumber.from_str("T0001V0103F00L00N000B")
        result = sanitize_serial_number_input(sn)
        self.assertEqual(result, [sn])

    def test_list_of_strings_and_serial_numbers(self) -> None:
        """Test mixed list of strings and SerialNumber objects."""
        sns = [
            SerialNumber.from_str(s)
            for s in [
                "T0001V0103F00L00N000A",
                "T0001V0103F00L00N000B",
                "T0001V0103F00L00N000C",
                "T0001V0103F00L00N000C",
            ]
        ]
        for i in range(2 ** len(sns)):
            raw_input = [str(sns[j]) if (i >> j) & 1 else sns[j] for j in range(len(sns))]
            with self.subTest(raw_input=raw_input):
                result = sanitize_serial_number_input(raw_input)
                self.assertEqual(result, sns)

    def test_bad_input_type(self) -> None:
        """Test that function rejects integer input."""
        with self.assertRaises(ExceptionGroup) as exc:
            sanitize_serial_number_input(12345)  # type: ignore [arg-type]
        self.assertEqual(len(exc.exception.exceptions), 1)
        self.assertIsInstance(exc.exception.exceptions[0], TypeError)

    def test_invalid_string_input(self) -> None:
        """Test that function rejects invalid serial number strings."""
        bad_strings = [
            "INVALID_SN_1",
            "T0001V0103F00L00N00GZ",  # Invalid hex character 'G'
            "T0001V0103F00L00",  # Too short
            "T0001V0103F00L00N000AEXTRA",  # Too long
        ]
        with self.assertRaises(ExceptionGroup) as exc:
            sanitize_serial_number_input(bad_strings)
        self.assertEqual(len(exc.exception.exceptions), len(bad_strings))
        for sub_exc in exc.exception.exceptions:
            self.assertIsInstance(sub_exc, ValueError)

    def test_mixed_input(self) -> None:
        """Test mixed valid and invalid inputs."""
        valid_sn = SerialNumber.from_str("T0001V0103F00L00N000A")
        raw_input = [
            valid_sn,
            "T0001V0103F00L00N000B",
            "INVALID_SN",
            12345,
        ]
        with self.assertRaises(ExceptionGroup) as exc:
            sanitize_serial_number_input(raw_input)  # type: ignore [arg-type]
        self.assertEqual(len(exc.exception.exceptions), 2)
        self.assertIsInstance(exc.exception.exceptions[0], ValueError)
        self.assertIsInstance(exc.exception.exceptions[1], TypeError)


if __name__ == "__main__":
    unittest.main()
