"""Structures for use in wrapping methods of classes (via metaclasses) or objects.

Source: https://web.archive.org/web/20200124090402id_/http://www.voidspace.org.uk/python/articles/metaclasses.shtml#a-method-decorating-metaclass
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from types import FunctionType, MethodType
from typing import Callable

_logger = logging.getLogger(__name__)


@dataclass()
class MethodFilter:
    """Data structure representing a filter for sub-selecting methods of a class or object.

    :param skip_private_methods: If True, methods starting with an underscore (_) will be skipped.
        Defaults to True.
    :param skip_dunder_methods: If True, methods with double underscores (e.g., __init__) will be
        skipped. Defaults to True
    :param methods_to_skip: A list of regexes for method names to additionally skip. Defaults to
        an empty list.
    :param compiled_skip_patterns: methods_to_skip compiled into regex patterns for efficiency.
    """

    skip_private_methods: bool = True
    skip_dunder_methods: bool = True
    methods_to_skip: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Compile regex patterns for methods to skip after initialization."""
        self._compiled_skip_patterns = [re.compile(pattern) for pattern in self.methods_to_skip]

    @property
    def compiled_skip_patterns(self) -> list[re.Pattern]:
        """Get the compiled regex patterns for methods to skip."""
        return self._compiled_skip_patterns

    def apply(self, method_names: list[str]) -> list[bool]:
        """Determine which methods to wrap based on this MethodFilter.

        :param method_names: A list of method names to evaluate.

        :return: List of strings from method_names that passed the filter.
        """
        retval: list[bool] = [False] * len(method_names)
        for i, name in enumerate(method_names):
            if self.skip_dunder_methods and name.startswith("__") and name.endswith("__"):
                _logger.debug("  skip dunder method: %s", name)
                continue

            if self.skip_private_methods and name.startswith("_"):
                _logger.debug("  skip private method: %s", name)
                continue

            found_regex_match = False
            for pattern in self.compiled_skip_patterns:
                if pattern.match(name):
                    found_regex_match = True
                    _logger.debug("skip match for %s: %s", pattern.pattern, name)
                    break
            if found_regex_match:
                continue

            retval[i] = True

        return retval


def method_wrapping_metaclass_factory(
    wrapper_function: Callable[[Callable], Callable],
    method_filter: MethodFilter | None = None,
) -> type:
    """Create a metaclass that wraps inheriting class's methods with a given function.

    :param wrapper_factory: A method that takes a function as input and returns a new
    function that wraps the original function.
    :param method_filter: An optional MethodFilter to specify which methods to skip wrapping.
        Uses the default MethodFilter if None provided (see help(core.MethodFilter) for details).

    :return: A metaclass that wraps specified methods with the provided function.

    :example:
        import wrapt  # type: ignore [import-untyped]
        from core.metaclasses import method_wrapping_metaclass_factory

        @wrapt.decorator
        def my_wrapper(wrapped, instance, args, kwargs):
            print("Wrapped!")
            return wrapped(*args, **kwargs)

        MyMetaclass = method_wrapping_metaclass_factory(
            my_wrapper, methods_to_skip=["method_to_skip"], skip_private_methods=True
        )

        class MyClass(metaclass=MyMetaclass):  # type: ignore [metaclass]
            def method_to_wrap(self, x):
                return x * 2

            def method_to_skip(self, y):
                return y + 3

            def _private_method(self, z):
                return z - 1

        obj = MyClass()
        obj.method_to_wrap(5)  # This will print "Wrapped!"
        obj.method_to_skip(5)  # This will not print any messages
        obj._private_method(5)  # This will not print any messages
    """
    method_filter_arg = method_filter or MethodFilter()

    class MethodWrappingMetaclass(type):
        "A metaclass that wraps class methods with a specified function."

        method_filter: MethodFilter = method_filter_arg

        def __new__(cls, class_name, bases, class_dict) -> MethodWrappingMetaclass:
            _logger.debug("Wrapping methods of class: %s", cls)
            new_class_dict = {}
            attr_names = list(class_dict.keys())
            target_attr_mask = cls.method_filter.apply(attr_names)

            for i, attr_name in enumerate(attr_names):
                if target_attr_mask[i]:
                    attr_value = class_dict[attr_name]
                    if isinstance(attr_value, (FunctionType, MethodType)):
                        attr_value = wrapper_function(attr_value)
                        _logger.debug("Y | wrapping attr: %s", attr_name)
                    else:
                        _logger.debug("X | attr is not method: %s", attr_name)

                    new_class_dict[attr_name] = attr_value

                else:
                    _logger.debug("X | attr flagged to skip: %s", attr_name)
                    new_class_dict[attr_name] = class_dict[attr_name]

            return super().__new__(cls, class_name, bases, new_class_dict)

    return MethodWrappingMetaclass


def wrap_object_methods(
    target_object: object,
    wrapper_function: Callable[[Callable], Callable],
    method_filter: MethodFilter | None = None,
) -> None:
    """Wrap all methods of a given object except those specified.

    :param target_object: The object whose methods are to be wrapped.
    :param wrapper_function: A method that takes a function as input and returns a new
    function wrapping the original.
    :param methods_to_skip: A list of method names to skip wrapping. Defaults to None.
    :param skip_private_methods: If True, methods starting with an underscore (_) will be skipped.

    :return: Nothing, modifies the object in-place.
    """
    method_filter = method_filter or MethodFilter()
    _logger.debug("Wrapping methods of object: %s", target_object)
    attr_names = list(dir(target_object))
    target_attr_mask = method_filter.apply(attr_names)

    for i, attr_name in enumerate(attr_names):
        if target_attr_mask[i]:
            attr_value = getattr(target_object, attr_name)
            if isinstance(attr_value, (FunctionType, MethodType)):
                wrapped_method = wrapper_function(attr_value)
                setattr(target_object, attr_name, wrapped_method)
                _logger.debug("Y | wrapping attr: %s", attr_name)
            else:
                _logger.debug("X | attr is not method: %s", attr_name)
        else:
            _logger.debug("X | attr flagged to skip: %s", attr_name)
