"""Function decorators for logging diagnostic data."""

import inspect
import logging
from datetime import datetime
from functools import update_wrapper
from typing import Callable, ParamSpec, TypeVar

Params = ParamSpec("Params")
ReturnType = TypeVar("ReturnType")


def log_timer_factory(
    logger: logging.Logger,
) -> Callable[[Callable[Params, ReturnType]], Callable[Params, ReturnType]]:
    """Create a decorator that logs the duration of a function call."""

    def log_timer_decorator(wrapped: Callable[Params, ReturnType]) -> Callable[Params, ReturnType]:
        """Decorator that logs the duration of a function call."""

        def log_duration(*args: Params.args, **kwargs: Params.kwargs) -> ReturnType:
            """Log start time, end time, and duration of decorated function."""
            start = datetime.now()
            retval = wrapped(*args, **kwargs)
            end = datetime.now()
            logger.info(
                '{"log_duration_data": {"func_name": "%s", "start": "%s", "end": "%s", "delta": %s}}',
                wrapped.__qualname__,
                start,
                end,
                (end - start).total_seconds(),
            )
            return retval

        return update_wrapper(log_duration, wrapped)

    return log_timer_decorator


def log_enter_exit_factory(
    logger: logging.Logger,
) -> Callable[[Callable[Params, ReturnType]], Callable[Params, ReturnType]]:
    """Creates a decorator that logs to a provided logger."""

    def log_enter_exit_decorator(
        wrapped: Callable[Params, ReturnType],
    ) -> Callable[Params, ReturnType]:
        """Decorator that logs function entry, arguments, return values, and exceptions."""

        def log_enter_exit(*args: Params.args, **kwargs: Params.kwargs) -> ReturnType:
            """Log function entry, arguments, return values, and exceptions."""
            func_args = inspect.signature(wrapped).bind(*args, **kwargs).arguments
            # Unpack function arguments into DEBUG log message
            logger.debug(
                "%s(%s)",
                wrapped.__qualname__,
                ", ".join(
                    map(
                        "{0[0]}={0[1]!r}".format,  # pylint: disable=consider-using-f-string
                        [(k, v) for k, v in func_args.items() if k != "self"],
                    )
                ),
            )
            try:
                retval = wrapped(*args, **kwargs)
            except Exception as err:
                logger.error("%s(...) raised %s(%s)", wrapped.__qualname__, type(err).__name__, err)
                logger.debug(err, exc_info=True)
                raise

            # log return values
            retval_tuple = (retval,) if not isinstance(retval, tuple) else retval
            logger.debug(
                "%s(...) returned %s",
                wrapped.__qualname__,
                ", ".join(repr(value) for value in retval_tuple),
            )
            return retval

        return update_wrapper(log_enter_exit, wrapped)

    return log_enter_exit_decorator
