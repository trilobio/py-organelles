"""Integration test for DurationFormatter."""
import time
import logging

from log_tools.formatters import DurationFormatter

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
