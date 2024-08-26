"""Custom logging.Formatters for your joy and convenience."""

import datetime
import logging
import time

COLOR_BRIGHT_RED = "\x1b[91m"
COLOR_BRIGHT_YELLOW = "\x1b[93m"
COLOR_RED = "\x1b[31m"
COLOR_BLUE = "\x1b[34m"
COLOR_WHITE = "\x1b[37m"
COLOR_RESET = "\x1b[0m"


class ColorFormatter(logging.Formatter):
    """Formatter that uses ANSI escape codes to color messages based on logging level.

    References:
        https://alexandra-zaharia.github.io/posts/make-your-own-custom-color-formatter-with-python-logging/
    """

    def __init__(self, *args, **kwargs):
        """Instantiate new ColorFormatter.

        for full docs, see help(logging.Formatter)
        """
        self._ansi_codes = {
            "NOTSET": "",
            "DEBUG": COLOR_BLUE,
            "INFO": COLOR_WHITE,
            "WARNING": COLOR_BRIGHT_YELLOW,
            "ERROR": COLOR_RED,
            "CRITICAL": COLOR_BRIGHT_RED,
        }
        super().__init__(*args, **kwargs)

    def format(self, record: logging.LogRecord) -> str:
        """Add respective color to start of record, escape code to end of record.

        If unrecognized levelname, uses NOTSET formatting.
        """
        try:
            ansi_start_code = self._ansi_codes[record.levelname]
        except KeyError:
            ansi_start_code = self._ansi_codes["NOTSET"]

        msg = super().format(record)
        return ansi_start_code + msg + COLOR_RESET

    def set_color(self, levelname: str, ansi_code: str) -> None:
        """Update ansi_code assigned to levelname.

        Note:
            Capitalizes 'levelname' before storing internally.
        """
        if not isinstance(levelname, str):
            raise TypeError(f"arg levelname expected 'str', not {type(levelname)}")
        if not isinstance(ansi_code, str):
            raise TypeError(f"arg ansi_code expected 'str', not {type(ansi_code)}")
        self._ansi_codes[levelname.upper()] = ansi_code

    def get_color(self, levelname: str) -> str:
        """Query ansi_code assigned to levelname."""
        if not isinstance(levelname, str):
            raise TypeError(f"arg levelname expected 'str', not {type(levelname)}")
        return self._ansi_codes[levelname.upper()]


class DurationFormatter(logging.Formatter):
    """Formatter that adds duration to log messages.

    References:
        https://stackoverflow.com/a/58943125

    Example:
    ```
    from log_tools import DurationFormatter
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    formatter = DurationFormatter(fmt="%(timedelta)s: %(message)s")

    handler.setFormatter(formatter)
    logger.add_handler(handler)
    ```
    """

    def __init__(self, *args, **kwargs):
        """Instantiate new DurationFormatter.

        for full docs, see help(logging.Formatter)
        """
        self.update_start_time()
        super().__init__(*args, **kwargs)

    def format(self, record: logging.LogRecord) -> str:
        """Add timedelta to start of record."""
        duration = datetime.datetime.utcfromtimestamp(record.created - self._start_time)
        record.timedelta = duration.strftime("%H:%M:%S")
        return super().format(record)

    @property
    def start_time(self) -> float:
        """Return acstime from which duration is calculated."""
        return self._start_time

    @start_time.setter
    def start_time(self, value: float) -> None:
        """Set asctime from which duration is calculated."""
        if not isinstance(value, (int, float)):
            raise TypeError(f"arg value expected 'int' or 'float', not {type(value)}")

        self._start_time = value

    def update_start_time(self) -> None:
        """Reset formatter start_time to time.time()"""
        self._start_time = time.time()
