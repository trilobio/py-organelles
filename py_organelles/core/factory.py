"""Module for creating standardized object factories."""

import logging
from typing import Any, Callable

_logger = logging.getLogger(__name__)

# This typing has been made less strict to allow for the usage of
# ObjectFactory in tcode.engine.validation to register validation methods
# Using type[tcode_api.api.TCode] instances as keys
FactoryKey = Any  # enum.Enum | str | int | KindInterface


class BuilderNotFoundError(Exception):
    """Exception raised when a builder is not found in the factory."""


class ObjectFactory:
    """A factory for creating objects."""

    def __init__(self, name: str | None = None) -> None:
        self._builders: dict[FactoryKey, Callable] = {}
        self.name = name or self.__class__.__name__

    def register_builder(self, key: FactoryKey, builder: Callable, override: bool = False) -> None:
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

    def create(self, key: FactoryKey, *args, **kwargs) -> Any:
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
        except KeyError as err:
            raise BuilderNotFoundError(f"{self.name} has no builder registered with {key}") from err

        return builder(*args, **kwargs)

    def __contains__(self, item: FactoryKey) -> bool:
        """Check if a builder is registered for the given key."""
        return item in self._builders


class MultiBuilderObjectFactory:
    """A factory for creating objects that exposes multiple builders, selectable by key."""

    def __init__(self, builder_kinds: list[str], name: str | None = None) -> None:
        """Create internal structure for organizing and storing builders."""
        self._builders: dict[str, dict[FactoryKey, Callable]] = {kind: {} for kind in builder_kinds}
        self.name = name or self.__class__.__name__

    def register_builder(
        self, builder_kind: str, key: FactoryKey, builder: Callable, override: bool = False
    ) -> None:
        """Register new builder with key.

        :param builder_kind: The builder_kind underneath which to register the provided builder.
            Must have been provided to the factory on __init__.
        :param key: The key to associate with the builder.
        :param builder: The builder to register.
        :param override: Override reviously registered builder, defaults to False.

        :raises ValueError: If builder_kind is not recognized with the factory.
        :raises ValueError: If override is False and key already has a registered builder.
        """
        if builder_kind not in self._builders:
            _logger.error("builder_kind=%s, options=%s", builder_kind, list(self._builders.keys()))
            raise ValueError(
                f"builder kind '{builder_kind}' not provided on factory __init__, is invalid"
            )

        if not override and key in self._builders:
            _logger.error("key=%s, options=%s", key, list(self._builders[builder_kind].keys()))
            raise ValueError(key)

        self._builders[builder_kind][key] = builder

    def build(self, builder_kind: str, key: FactoryKey, *args, **kwargs) -> Any:
        """Build an object using the builder addressed by builder_kind and key.

        :param builder_kind: The builder_kind to use
        :param key: The key to use
        :param args: Positional arguments to pass to the builder.
        :param kwargs: Keyword arguments to pass to the builder.

        :raises ValueError: If builder_kind is not recognized with the factory.
        :raises ValueError: If key does not have a registered builder of kind builder_kind.

        :return: The object created by the builder associated with key.
        """
        if builder_kind not in self._builders:
            _logger.error("builder_kind=%s, options=%s", builder_kind, list(self._builders.keys()))
            raise ValueError(f"{self.name} has no builder kind {builder_kind} registered")

        if key not in self._builders[builder_kind]:
            _logger.error("key=%s, options=%s", key, list(self._builders[builder_kind].keys()))
            raise BuilderNotFoundError(
                f"{self.name} has no builder registered with {builder_kind} for key {key}"
            )

        try:
            return self._builders[builder_kind][key](*args, **kwargs)
        except TypeError as err:
            _logger.error(
                "Failed to call builder with key=%s, builder_kind=%s, args=%s, kwargs=%s",
                key,
                builder_kind,
                args,
                kwargs,
            )
            raise err

    def register_builder_kind(self, builder_kind: str) -> None:
        """Add a new builder kind to the factory.

        :param builder_kind: The name of the new builder kind to add.
        """
        if builder_kind not in self._builders:
            self._builders[builder_kind] = {}
