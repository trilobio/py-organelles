"""Module for creating standardized object factories."""

import enum
import logging
import typing as _t


_logger = logging.getLogger("core.factory")

KeyType = enum.Enum | str | int


class ObjectFactory:
    """A factory for creating objects."""

    def __init__(self) -> None:
        self._builders = {}

    def register_builder(self, key: KeyType, builder: _t.Callable, override: bool = False) -> None:
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
                f"{key} already has a registered builder; " "provide override=True to replace it"
            )

        self._builders[key] = builder

    def create(self, key: KeyType, *args, **kwargs) -> _t.Any:
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


class MultiBuilderObjectFactory:
    """A factory for creating objects that exposes multiple builders, selectable by key."""

    def __init__(self, builder_kinds: list[str]) -> None:
        """Create internal structure for organizing and storing builders."""
        self._builders: dict[str, dict[KeyType, _t.Callable]] = {kind: {} for kind in builder_kinds}

    def register_builder(self, builder_kind: str, key: KeyType, builder: _t.Callable, override: bool = False) -> None:
        """Register new builder with key.

        @param builder_kind: The builder_kind underneath which to register the provided builder.
            Must have been provided to the factory on __init__.
        @type builder_kind: str
        @param key: The key to associate with the builder.
        @type key: multiple options, primarily enum.Enum or str
        @param builder: The builder to register.
        @type builder: Callable
        @param override: Override reviously registered builder, defaults to False.
        @type override: bool, optional

        @raises ValueError: If builder_kind is not recognized with the factory.
        @raises ValueError: If override is False and key already has a registered builder.
        """
        if builder_kind not in self._builders:
            _logger.error("builder_kind=%s, options=%s", builder_kind, list(self._builders.keys()))
            raise ValueError(builder_kind)

        if not override and key in self._builders:
            _logger.error("key=%s, options=%s", key, list(self._builders[builder_kind].keys()))
            raise ValueError(key)

        self._builders[builder_kind][key] = builder

    def build(self, builder_kind: str, key: KeyType, *args, **kwargs) -> _t.Any:
        """Build an object using the builder addressed by builder_kind and key.

        @param builder_kind: The builder_kind to use
        @type builder_kind: str
        @param key: The key to use
        @type key: multiple options, primarily enum.Enum or str
        @param args: Positional arguments to pass to the builder.
        @type args: tuple
        @param kwargs: Keyword arguments to pass to the builder.
        @type kwargs: dict

        @raises ValueError: If builder_kind is not recognized with the factory.
        @raises ValueError: If key does not have a registered builder of kind builder_kind.

        @return: The object created by the builder associated with key.
        @rtype: Fully dependent on the constructors registered with the factorAnyy
        """
        if builder_kind not in self._builders:
            _logger.error("builder_kind=%s, options=%s", builder_kind, list(self._builders.keys()))
            raise ValueError(builder_kind)

        if key not in self._builders[builder_kind]:
            _logger.error("key=%s, options=%s", key, list(self._builders[key].keys()))
            raise ValueError(key)

        return self._builders[builder_kind][key](*args, **kwargs)
