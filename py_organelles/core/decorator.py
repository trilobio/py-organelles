"""Generic module for better decorator factories.

Notes:
    - Built based on GrahamDumpleton's github-based blog on decorators:
        https://github.com/GrahamDumpleton/wrapt/blob/develop/blog/01-how-you-implemented-your-python-decorator-is-wrong.md

    - Not implemented far enough to support @classmethod or @staticmethod stacked decorating yet.
    - Initially motivated by the inability to use decorators in conjunction with @plac.annotation as follows:
```
@plac.annotations(robot_name=robot_name_annotation)
@prettify_can_errors
def main(robot_name: str) -> None:
    pass
```
raises error:
```
Traceback (most recent call last):
  File "/home/trilo/aceta/robot/scripts/unit-tests/j1_wrapping.py", line 72, in <module>
    plac.call(main)
  File "/home/trilo/.cache/pypoetry/virtualenvs/robot-BUTdGB3R-py3.11/lib/python3.11/site-packages/plac_core.py", line 436, in call
    cmd, result = parser.consume(arglist)
                  ^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/trilo/.cache/pypoetry/virtualenvs/robot-BUTdGB3R-py3.11/lib/python3.11/site-packages/plac_core.py", line 287, in consume
    return cmd, self.func(*(args + varargs + extraopts), **kwargs)
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/trilo/aceta/robot/robot/ui/cli.py", line 111, in dec
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
TypeError: main() takes from 1 to 2 positional arguments but 3 were given
```
"""
import functools
import typing as _t


class _ObjectProxy:
    """Object proxy class to expose descriptor interface.

    https://github.com/GrahamDumpleton/wrapt/blob/develop/blog/02-the-interaction-between-decorators-and-descriptors.md#transparent-object-proxy
    """

    def __init__(self, wrapped):
        self.wrapped = wrapped
        try:
            self.__name__ = self.wrapped.__name__
        except AttributeError:
            pass

    @property
    def __class__(self):
        return self.wrapped.__class__

    def __getattr__(self, name: str) -> _t.Any:
        return getattr(self.wrapped, name)


class _BoundFunctionWrapper(_ObjectProxy):
    """Wrapper class for functions bound to class instances.

    ex. methods, including @classmethod and @staticmethod
    """

    def __init__(self, wrapped, instance, wrapper):
        """Instantiate a _BoundFunctionWrapper.

        Args:
            wrapped (object): object to wrap (function, method, class)
            instance (object): if wrapped is a method, instance is the class, else None
            wrapper (object): object to call (ex. your decorator)
                Must take Callable as 1st arg, Optional instance as 2nd arg
        """
        super().__init__(wrapped)
        self.instance = instance
        self.wrapper = wrapper

    def __call__(self, *args, **kwargs) -> _t.Any:
        if self.instance is None:  # If wrapped isn't a method, OR was called like a function
            instance, args = args[0], args[1:]
            wrapped = functools.partial(self.wrapped, instance)
            return self.wrapper(wrapped, instance, *args, **kwargs)

        return self.wrapper(self.wrapped, self.instance, *args, **kwargs)


class _FunctionWrapper(_ObjectProxy):
    """Wrapper class for functions."""

    def __init__(self, wrapped, wrapper):
        """Instantiate a _FunctionWrapper.

        Args:
            wrapped (object): object to wrap (function, method, class)
            wrapper (object): object to call (ex. your decorator)
                Must take Callable as 1st arg, Optional instance as 2nd arg
        """
        super().__init__(wrapped)
        self.__doc__ = wrapped.__doc__  # FIXME (connor): seems like the wrong way to do this
        self.wrapper = wrapper

    def __get__(self, instance, owner) -> _BoundFunctionWrapper:
        wrapped = self.wrapped.__get__(instance, owner)
        return _BoundFunctionWrapper(wrapped, instance, self.wrapper)

    def __call__(self, *args, **kwargs) -> _t.Any:
        return self.wrapper(self.wrapped, None, *args, **kwargs)


def wrapper_to_decorator(wrapper: _t.Callable) -> _t.Callable:
    """Creates a decorator out of the decorated function.

    Usage:
       decorates a function with the following interface:
       `def f(func: Callable, instance: Any, *args, **kwargs) -> Any:`
           - `func` is the function being decorated
           - `instance` is the instance of the class on which the method is called if
           the decorated function is a method, otherwise it's None
           - 'args' and 'kwargs' are the arguments passed to the function being decorated

    Example:
    ```
    @wrapper_to_decorator
    def print_args(func: Callable, instance: Any, *args, **kwargs) -> Any:
        \"\"\"Decorator that prints the args of the function\"\"\"
        print(f'args={','.join([str(a) for a in args])}')
        return func(*args, **kwargs)

    @print_args
    def add(a: int, b: int) -> int:
        return a + b

    add(1, 2)

    > args=1,2

    Args:
        wrapper (Callable): callable object to decorate, typically itself
            intended for use as as a decorator.

    Returns:
        wrapper function, but made into decorator (see Usage)
    """

    @functools.wraps(wrapper)
    def _decorator(wrapped: _t.Callable) -> _FunctionWrapper:
        """Wrap the function on which the decorator is applied in a _FunctionWrapper."""
        return _FunctionWrapper(wrapped, wrapper)

    return _decorator
