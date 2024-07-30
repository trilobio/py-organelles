"""Unsorted logging tools."""
import logging
from typing import List, Optional

def get_handlers(logger: logging.Logger) -> List[logging.Handler]:
    """Recursively traverse logger hierarchy and return list of all handlers applying to given logger."""
    if not logger.hasHandlers():
        handlers = []

    elif logger.parent is not None:
        p_handlers = get_handlers(logger.parent)
        handlers = [h for h in logger.handlers if h not in p_handlers] + p_handlers

    else:
        handlers = logger.handlers

    return handlers


def _get_handler_formatter_str(handler: logging.Handler) -> Optional[str]:
    return handler.formatter._fmt if handler.formatter is not None else None


def _handlers_are_similar(h1: logging.Handler, h2: logging.Handler) -> bool:
    """Return True if handlers are similar."""
    return _get_handler_formatter_str(h1) == _get_handler_formatter_str(h2)\
        and h1.get_name() == h2.get_name()\
        and h1.level == h2.level\
        and h1.__class__ == h2.__class__


def has_similar_handler(logger: logging.Logger, handler: logging.Handler) -> bool:
    """Return True if given logger has a handler that closely matches handler."""
    # No handlers in logger hierarchy means no duplicates
    if not logger.hasHandlers():
        return False

    for l_handler in get_handlers(logger):
        if _handlers_are_similar(l_handler, handler):
            return True

    return False
