import json
import unittest

from log_tools import StructuredJSONMessage


class TestStructuredJSONMessage(unittest.TestCase):

    def test_json_intake_message(self) -> None:
        """Verify that str() representation of StructuredJSONMessage is a valid JSON string."""
        messages = [
            StructuredJSONMessage("a message", a=1, b=0.1, c="args"),
            StructuredJSONMessage(""),
        ]
        for message in messages:
            with self.subTest(message=message):
                json.loads(str(message))  # This should not raise an exception

    def test_message_kwarg_protection(self) -> None:
        """Verify that 'message' keyword is protected."""
        with self.assertRaises(ValueError):
            StructuredJSONMessage("a message", message="should not be allowed")

    def test_timestamp_default(self) -> None:
        """Verify that 'timestamp' is set by default."""
        message = StructuredJSONMessage("a message")
        self.assertIn("timestamp", json.loads(str(message)))

        timestamp = "A timestamp"
        message = StructuredJSONMessage("another message", timestamp=timestamp)
        self.assertEqual(json.loads(str(message))["timestamp"], timestamp)
