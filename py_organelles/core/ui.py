"""plac-related user interface functions."""

import plac


def create_annotation_from_enum(enum_class: type, kind: str = "positional") -> plac.Annotation:
    """Generate plac annotation from enum class.

    Example:
        ```
        import enum
        import plac

        from core.ui import create_annotation_from_enum

        class Color(enum.Enum):
            RED = enum.auto()
            GREEN = enum.auto()
            BLUE = enum.auto()

        @plac.annotations(
            color=create_annotation_from_enum(MyEnum)
        )
        def main(color: Color) -> None:
            print(color.name)

        if __name__ == "__main__":
            plac.call(main)
        ```

    Args:
        enum_class (type): Enum class from which to generate annotation.
        kind (str): Passed to plac.Annotation. Defaults to 'positional'.

    Returns:
        plac.Annotation: Generated Annotation object.
    """
    return plac.Annotation(
        help=f"one of {[e.name for e in enum_class]}",
        kind=kind,
        type=enum_class.__getitem__,
    )
