"""Integration test for DurationFormatter."""

import logging
import time

from py_organelles.log_tools import DurationFormatter


def main() -> None:
    _logger_name = "__name__"
    logger = logging.getLogger(_logger_name)
    handler = logging.StreamHandler()
    formatter = DurationFormatter("%(timedelta)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.setLevel(logging.INFO)
    handler.setLevel(logging.INFO)

    for i in range(1, 4):
        time.sleep(i)
        logger.info("Slept for %s seconds", i)

    formatter.update_start_time()
    logger.info("Updated start_time")

    for i in range(5):
        time.sleep(i)
        logger.info("Slept for %s seconds", i)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
