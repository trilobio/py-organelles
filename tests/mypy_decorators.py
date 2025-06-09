"""Run this file through mypy - you should get errors."""

import logging
from typing import TYPE_CHECKING

from log_tools.decorators import log_timer_factory


@log_timer_factory(logging.getLogger(__name__))
def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y


logging.basicConfig(level=logging.INFO)
add(1, 2)


if __name__ == "__main__":
    # Turn to True to run the mypy checks
    if TYPE_CHECKING and False:
        # Mypy should raise errors for the following calls
        add(1, "2")
        add()
        add(1, 2, 3)
