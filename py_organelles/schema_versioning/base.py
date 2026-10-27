"""Base class for schema-versioned pydantic models."""

from abc import ABC
from typing import Self, TextIO

from pydantic import BaseModel


class BaseSchemaVersionedModel(BaseModel, ABC):
    """pydantic BaseModel with a ``schema_version`` field.

    Sets no ``model_config``, so that each project can mix in its own configured base model, e.g.
    ``class MyBase(MyConfiguredModel, BaseSchemaVersionedModel)``.

    :note: ``read()`` and ``write()`` methods are exposed on this class because
        only schema-versioned models should be read from and written to JSON blobs.
    """

    schema_version: int

    @classmethod
    def read(cls, file_object: TextIO) -> Self:
        """Load a model from a file-like object.

        :param file_object: A file-like object (typically created via ``open('r')``).

        :returns: The loaded model.
        """
        data = file_object.read()
        return cls.model_validate_json(data)

    def write(self, file_object: TextIO) -> None:
        """Write the model to a file-like object.

        :param file_object: A file-like object (typically created via ``open('w')``).
        """
        data = self.model_dump_json(indent=2)
        file_object.write(data)
