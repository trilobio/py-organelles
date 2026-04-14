"""Command-line user prompting functions."""


def prompt_yes_no(prompt: str, default: bool = False) -> bool:
    """Prompt for yes/no; re-prompts until valid input. Type 'q' to cancel.

    :param prompt: A string to display when asking the user for input.
    :param default: The default boolean value to return if the user just presses Enter.
    :return: The boolean value corresponding to the user's input.
    """
    hint = "[Y/n/q]" if default else "[y/N/q]"
    while True:
        raw = input(f"{prompt} {hint} ").strip().lower()
        if raw == "":
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        if raw in ("q", "quit"):
            raise SystemExit("Cancelled.")
        print("  Please enter 'y', 'n', or 'q' to quit.")


def prompt_choice(label: str, options: list[str]) -> int:
    """Display a numbered menu; return 0-based index of chosen item. Type 'q' to cancel.

    :param label: A string to display above the menu options.
    :param options: A list of strings to display as menu options.

    :return: The 0-based index of the chosen option.
    """
    n = len(options)
    print(f"\n{label}")
    for i, opt in enumerate(options):
        print(f"  {i + 1}) {opt}")
    print("  q) Quit")
    while True:
        raw = input(f"Select [1-{n}/q]: ").strip().lower()
        if raw in ("q", "quit"):
            raise SystemExit("Cancelled.")
        if raw.isdigit() and 1 <= int(raw) <= n:
            return int(raw) - 1
        print(f"  Please enter a number between 1 and {n}, or 'q' to quit.")
