"""Generic useful context managers."""
import typing as _t
from contextlib import contextmanager


@contextmanager
def modify_attribute(obj: _t.Any, attribute_name: str, new_value: _t.Any):
    # Save the original value
    original_value = getattr(obj, attribute_name, None)

    try:
        # Modify the attribute
        setattr(obj, attribute_name, new_value)
        yield
    finally:
        # Reset the attribute to its original value on exit
        setattr(obj, attribute_name, original_value)
