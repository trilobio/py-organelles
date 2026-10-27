"""Unittests for serial_number.py"""

import unittest

from py_organelles import (
    Factory,
    ProductType,
    SerialNumber,
    generate_serial_numbers,
    sanitize_serial_number_input,
)


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

        b = b"\x0b\x00\x00\x00\x03\x01\x01\x00"
        self.assertEqual(
            SerialNumber.from_bytes(b),
            SerialNumber(ProductType.trilobot, 1, 3, Factory.office, 0, 11),
        )

    def test_from_bytes_rejects_a_product_type_that_names_nothing(self) -> None:
        """Product type 10 is no member, and a serial number carrying one is not one."""
        with self.assertRaises(ValueError):
            SerialNumber.from_bytes(b"\x00\x01\x02\x00\x00\x00\x0a\x00")

    def test_to_bytes(self) -> None:
        """Test SerialNumber.to_bytes method."""
        b = b"\x0b\x00\x00\x00\x03\x01\x01\x00"
        sn = SerialNumber.from_bytes(b)
        self.assertEqual(b, sn.to_bytes())


class TestSerialNumberEnums(unittest.TestCase):
    """A serial number holds enum members however it was built."""

    def test_a_parsed_serial_number_holds_members_like_a_constructed_one(self) -> None:
        """`is` against a member has to work, or it is a trap.

        `ProductType` is an `IntEnum`, so a plain int compares equal to a member and
        nothing downstream notices the difference - until something uses `is`, which then
        passes every test built from the constructor and is wrong on every serial number
        read off the wire.
        """
        built = SerialNumber(ProductType.frame, 1, 6, Factory.office, 0, 1)

        for name, parsed in (
            ("from_str", SerialNumber.from_str(str(built))),
            ("from_int", SerialNumber.from_int(built.pack())),
            ("from_bytes", SerialNumber.from_bytes(built.to_bytes())),
        ):
            with self.subTest(constructor=name):
                self.assertIs(parsed.product_type, ProductType.frame)
                self.assertIs(parsed.factory, Factory.office)
                self.assertEqual(parsed, built)

    def test_a_product_type_that_names_nothing_is_refused(self) -> None:
        """Unknown hardware is a thing to add to the enum, not to carry as a number."""
        with self.assertRaises(ValueError):
            SerialNumber.from_str("T0000V0106F00L00N0001")

        with self.assertRaises(ValueError):
            SerialNumber.from_int(0xFFFFFFFFFFFFFFFF)

    def test_a_factory_that_names_nothing_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            SerialNumber.from_str("T0006V0106FFFL00N0001")


class TestGenerateSerialNumbers(unittest.TestCase):
    """Serial numbers for tests and mocks: well-formed, and all different."""

    def test_every_one_differs(self) -> None:
        """A constant would make two mock boards indistinguishable."""
        taken = [next(generate_serial_numbers(ProductType.trilobot)) for _ in range(5)]

        self.assertEqual(len(set(taken)), len(taken))

    def test_two_generators_never_collide(self) -> None:
        """The counter is shared, so interleaving two kinds stays unique."""
        robots = generate_serial_numbers(ProductType.trilobot)
        frames = generate_serial_numbers(ProductType.frame)

        taken = [next(robots), next(frames), next(robots), next(frames)]

        self.assertEqual(len(set(taken)), len(taken))

    def test_what_is_generated_says_what_it_was_asked_for(self) -> None:
        serial_number = next(
            generate_serial_numbers(ProductType.frame, version_major=1, version_minor=6)
        )

        self.assertIs(serial_number.product_type, ProductType.frame)
        self.assertEqual((serial_number.version_major, serial_number.version_minor), (1, 6))

    def test_what_is_generated_round_trips(self) -> None:
        """They stand in for real serial numbers, so they have to behave like them."""
        serial_number = next(generate_serial_numbers(ProductType.tool_pcb))

        self.assertEqual(SerialNumber.from_str(str(serial_number)), serial_number)


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
