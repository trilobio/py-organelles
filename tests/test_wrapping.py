"""Unittests for core.wrapping module."""

import unittest

import wrapt  # type: ignore [import-untyped]

from core import MethodFilter, method_wrapping_metaclass_factory, wrap_object_methods


class TestMethodWrappingMetaclassFactory(unittest.TestCase):
    """Unit tests for method_wrapping_metaclass_factory function."""

    def test_method_wrapping(self) -> None:
        """Test that methods are wrapped correctly."""

        @wrapt.decorator
        def store_args_wrapper(wrapped, instance, args, kwargs):
            instance.counter += 1
            return wrapped(*args, **kwargs)

        method_filter = MethodFilter(methods_to_skip=["method_to_skip"], skip_private_methods=True)
        TestMetaclass = method_wrapping_metaclass_factory(
            store_args_wrapper, method_filter=method_filter
        )

        class TestClass(metaclass=TestMetaclass):  # type: ignore [metaclass]

            def __init__(self):
                self.counter = 0

            def method_to_wrap(self, x):
                """A method that should be wrapped."""
                return x * 2

            def method_to_skip(self, y):
                """A method that should not be wrapped."""
                return y + 3

            def _private_method(self):
                """A private method that should not be wrapped."""
                return "private"

        obj = TestClass()
        self.assertEqual(obj.counter, 0)

        with self.subTest("Check that 'methods_to_skip' argument works"):
            obj.method_to_skip(5)
            self.assertEqual(obj.counter, 0)

        with self.subTest("Check that method wrapping works"):
            obj.method_to_wrap(7)
            self.assertEqual(obj.counter, 1)

        with self.subTest("Check that private methods are skipped"):
            obj._private_method()
            self.assertEqual(obj.counter, 1)

        # NOTE: this test ONLY passes when using wrapt to create the wrapper function.
        with self.subTest("Check wrapped method docstring maintenance"):
            # Check that wrapping maintained docstrings
            self.assertEqual(obj.method_to_wrap.__doc__, "A method that should be wrapped.")
            self.assertEqual(obj.method_to_skip.__doc__, "A method that should not be wrapped.")


class TestWrapObjectMethods(unittest.TestCase):
    """Unit tests for wrap_object_methods function."""

    def test_wrap_object_methods(self) -> None:
        """Test that object methods are wrapped correctly."""

        @wrapt.decorator
        def log_call_wrapper(wrapped, instance, args, kwargs):
            """Logs a wrapped method call by incrementing the object's internal counter."""
            instance.counter += 1
            return wrapped(*args, **kwargs)

        class TestClass:

            def __init__(self):
                self.counter = 0

            def method_one(self):
                """First method."""
                return "one"

            def method_two(self):
                """Second method."""
                return "two"

            def _method_three(self):
                """Third method (private)."""
                return "three"

        obj = TestClass()

        # Test that nothing is wrapped yet
        self.assertEqual(obj.counter, 0)
        obj.method_one()
        self.assertEqual(obj.counter, 0)
        obj.method_two()
        self.assertEqual(obj.counter, 0)
        obj._method_three()
        self.assertEqual(obj.counter, 0)

        method_filter = MethodFilter(methods_to_skip=["method_two"], skip_private_methods=True)
        wrap_object_methods(obj, log_call_wrapper, method_filter)

        # Check that 'methods_to_skip' argument works
        obj.method_two()
        self.assertEqual(obj.counter, 0)

        # Check that skip_private_methods argument works
        obj._method_three()
        self.assertEqual(obj.counter, 0)

        # Check that method wrapping works
        obj.method_one()
        self.assertEqual(obj.counter, 1)

        # Check that dunder methods aren't wrapped
        repr(obj)
        self.assertEqual(obj.counter, 1)

    def test_wrap_wrapped_object(self) -> None:
        """Test that nested wrapping doesn't cause issues."""

        @wrapt.decorator
        def inner_wrapper(wrapped, instance, args, kwargs):
            """Logs a wrapped method call by incrementing the object's counter A."""
            instance.counter_inner += 1
            return wrapped(*args, **kwargs)

        @wrapt.decorator
        def outer_wrapper(wrapped, instance, args, kwargs):
            """Logs a wrapped method call by incrementing the object's counter B."""
            instance.counter_outer += 1
            return wrapped(*args, **kwargs)

        class TestClass:

            def __init__(self):
                self.counter_inner = 0
                self.counter_outer = 0

            def method_double_wrapped(self):
                """Method to be wrapped by both wrappers."""

            def method_inner_only(self):
                """Method to be wrapped only by the inner wrapper."""

            def method_outer_only(self):
                """Method to be wrapped only by the outer wrapper."""

            def _method_private(self):
                """Private method."""

        obj = TestClass()

        # Test that nothing is wrapped yet
        self.assertEqual(obj.counter_inner, 0)
        self.assertEqual(obj.counter_outer, 0)
        obj.method_double_wrapped()
        self.assertEqual(obj.counter_inner, 0)
        self.assertEqual(obj.counter_outer, 0)
        obj.method_inner_only()
        self.assertEqual(obj.counter_inner, 0)
        self.assertEqual(obj.counter_outer, 0)
        obj.method_outer_only()
        self.assertEqual(obj.counter_inner, 0)
        self.assertEqual(obj.counter_outer, 0)
        obj._method_private()
        self.assertEqual(obj.counter_inner, 0)
        self.assertEqual(obj.counter_outer, 0)

        method_filter = MethodFilter(
            methods_to_skip=["method_outer_only"], skip_private_methods=True
        )
        wrap_object_methods(obj, inner_wrapper, method_filter)

        # Check that 'methods_to_skip' argument works
        obj.method_outer_only()
        self.assertEqual(obj.counter_inner, 0)
        self.assertEqual(obj.counter_outer, 0)

        # Check that skip_private_methods argument works
        obj._method_private()
        self.assertEqual(obj.counter_inner, 0)
        self.assertEqual(obj.counter_outer, 0)

        # Check that method wrapping works
        obj.method_inner_only()
        self.assertEqual(obj.counter_inner, 1)
        self.assertEqual(obj.counter_outer, 0)
        obj.method_double_wrapped()
        self.assertEqual(obj.counter_inner, 2)
        self.assertEqual(obj.counter_outer, 0)

        # Check that dunder methods aren't wrapped
        repr(obj)
        self.assertEqual(obj.counter_inner, 2)
        self.assertEqual(obj.counter_outer, 0)

        # Now wrap again with outer_wrapper
        method_filter = MethodFilter(
            methods_to_skip=["method_inner_only"], skip_private_methods=True
        )
        wrap_object_methods(obj, outer_wrapper, method_filter)
        obj.counter_inner = 0
        obj.counter_outer = 0

        # Check that skip_private_methods argument works
        obj._method_private()
        self.assertEqual(obj.counter_inner, 0)
        self.assertEqual(obj.counter_outer, 0)

        obj.method_outer_only()
        self.assertEqual(obj.counter_inner, 0)
        self.assertEqual(obj.counter_outer, 1)

        obj.method_inner_only()
        self.assertEqual(obj.counter_inner, 1)
        self.assertEqual(obj.counter_outer, 1)

        obj.method_double_wrapped()
        self.assertEqual(obj.counter_inner, 2)
        self.assertEqual(obj.counter_outer, 2)

        repr(obj)
        self.assertEqual(obj.counter_inner, 2)
        self.assertEqual(obj.counter_outer, 2)
