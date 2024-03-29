"""Generic useful context managers."""
import typing as _t
from contextlib import contextmanager


@contextmanager
def modify_attribute(
    obj: _t.Union[_t.Any, _t.List[_t.Any]],
    attribute_name: _t.Union[str, _t.List[str]],
    new_value: _t.Union[_t.Any, _t.List[_t.Any]],
) -> None:
    # Put all args in lists
    if not isinstance(obj, list):
        obj = [obj]

    if not isinstance(attribute_name, list):
        attribute_name = [attribute_name]

    if not isinstance(new_value, list):
        new_value = [new_value]

    # Validate arguments
    if not len(attribute_name) == len(new_value):
        raise ValueError("Must have same number of attributes and values")

    if not len(obj) == len(attribute_name):
        if len(obj) == 1:  # Repeat the same object for all attributes
            obj = obj * len(attribute_name)

        else:
            raise ValueError(
                "Must have 1 object OR same number of objects and attributes"
            )

    # Save the original values
    original_value: _t.List[_t.Any] = [None] * len(obj)
    for i, (o, a) in enumerate(zip(obj, attribute_name)):
        if hasattr(o, a):
            original_value[i] = getattr(o, a)

    try:
        # Modify the attributes
        for o, a, new_v in zip(obj, attribute_name, new_value):
            setattr(o, a, new_v)

        yield

    finally:
        # Reset the attribute to its original value on exit
        for o, a, orig_v in zip(obj, attribute_name, original_value):
            setattr(o, a, orig_v)
