"""Function decorators for logging diagnostic data."""

import inspect
import logging
from datetime import datetime
from typing import Any, Callable

from core import wrapper_to_decorator


def log_timer_factory(logger: logging.Logger) -> Callable:
    """Create a decorator that logs the duration of a function call."""

    @wrapper_to_decorator
    def log_duration(func: Callable, instance: Any, *args, **kwargs) -> Any:
        """Log start time, end time, and duration of decorated function."""
        start = datetime.now()
        retval = func(*args, **kwargs)
        end = datetime.now()
        logger.info(
            '{"log_duration_data": {"func_name": "%s", "start": "%s", "end": "%s", "delta": %s}}',
            func.__qualname__,
            start,
            end,
            (end - start).total_seconds(),
        )
        return retval

    return log_duration


def log_enter_exit_factory(logger: logging.Logger) -> Callable:
    """Creates a decorator that logs to a provided logger."""

    @wrapper_to_decorator
    def log_enter_exit(func: Callable, instance: Any, *args, **kwargs) -> Any:
        """Log function entry, arguments, return values, and exceptions."""
        func_args = inspect.signature(func).bind(*args, **kwargs).arguments
        # Unpack function arguments into DEBUG log message
        logger.debug(
            "%s(%s)",
            func.__qualname__,
            ", ".join(
                map(
                    "{0[0]}={0[1]!r}".format,  # pylint: disable=consider-using-f-string
                    [(k, v) for k, v in func_args.items() if k != "self"],
                )
            ),
        )
        try:
            retval = func(*args, **kwargs)
        except Exception as err:
            logger.error(err)
            logger.debug(err, exc_info=True)
            raise

        # log return values
        retval_tuple = (retval,) if not isinstance(retval, tuple) else retval
        logger.debug(
            "%s(...) returned %s",
            func.__qualname__,
            ", ".join(repr(value) for value in retval_tuple),
        )
        return retval

    return log_enter_exit
