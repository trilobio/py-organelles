"""Module for creating standardized object factories."""
import typing as _t


class ObjectFactory:
    """A factory for creating objects."""

    def __init__(self):
        self._builders = {}

    def register_builder(
        self, key, builder: _t.Callable, override: bool = False
    ) -> None:
        """Register new builder with key.

        Args:
            key: The key to associate with the builder.
            builder: The builder to register.
            override: Override reviously registered builder.
                Defaults to False.

        Raises:
            ValueError: If override is False and key already has a registered builder.
        """
        if not override and key in self._builders:
            raise ValueError(
                f"{key} already has a registered builder; "
                "provide override=True to replace it"
            )

        self._builders[key] = builder

    def create(self, key, *args, **kwargs) -> _t.Any:
        """Create an object using the builder associated with key.

        Args:
            key: The key associated with the builder to use.
            *args: Positional arguments to pass to the builder.
            **kwargs: Keyword arguments to pass to the builder.

        Returns:
            The object created by the builder associated with key.

        Raises:
            ValueError: If key does not have a registered builder.
        """
        try:
            builder = self._builders[key]
        except KeyError:
            raise ValueError(f"{key} does not have a registered builder")

        return builder(*args, **kwargs)
