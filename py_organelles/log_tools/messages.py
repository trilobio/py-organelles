"""Types of message classes for implementing structured logs.

Built referencing the standard python logging Cookbook:
    https://docs.python.org/3/howto/logging-cookbook.html#implementing-structured-logging
"""

import json
from datetime import datetime


class StructuredJSONMessage:
    """A class for creating structured JSON messages for logging."""

    def __init__(self, message: str, /, **kwargs) -> None:
        self.message = message
        self.kwargs = kwargs
        if "message" in kwargs:
            raise ValueError("The 'message' keyword argument is reserved and cannot be used.")
        if "timestamp" not in kwargs:
            self.kwargs["timestamp"] = (
                datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S.%f%z")
            )

    def __str__(self) -> str:
        return json.dumps({"message": self.message, **self.kwargs})
