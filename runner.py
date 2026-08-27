"""Developer task CLI.

Depends only on the Python standard library.

Usage:
    python runner.py <command> [-- <forwarded args>]

Commands:
    format [--nofix]   Format and lint with ruff. Default: reformat files and
                       auto-fix lint issues. With --nofix: check only, failing
                       instead of modifying files (intended for CI / hooks).
    lint               Type-check code with mypy.
    test               Run the test suite.
    all                Run format, lint, and test in sequence.

Anything after ``--`` is forwarded raw to the underlying tool (ruff / mypy /
unittest); e.g. ``runner.py test -- -k some_test -v``. Not allowed with ``all``.
"""

import argparse
import subprocess
import sys
from collections.abc import Sequence


def _rule(label: str) -> None:
    """Print a section header rule."""
    filler = "─" * max(0, 79 - len(label))
    print(f"── {label} {filler}", flush=True)


def _run(label: str, *args: str) -> bool:
    """Run a command, printing a header and a pass/fail footer.

    Returns True on success, False on failure.
    """
    _rule(label)
    result = subprocess.run(args)
    if result.returncode == 0:
        print(f"✓ {label} passed\n")
        return True
    print(f"✗ {label} failed (exit {result.returncode})\n")
    return False


def format_cmd(nofix: bool = False, forwarded: Sequence[str] = ()) -> None:
    """Format and lint with ruff.

    Default reformats files and auto-fixes lint issues. ``--nofix`` checks only:
    it does not modify files and exits non-zero if changes are needed.
    ``forwarded`` args are appended to each ruff invocation.
    """
    if nofix:
        steps = [
            ("ruff format --check", ["uv", "run", "ruff", "format", "--check"]),
            ("ruff check", ["uv", "run", "ruff", "check"]),
        ]
    else:
        steps = [
            ("ruff format", ["uv", "run", "ruff", "format"]),
            ("ruff check --fix", ["uv", "run", "ruff", "check", "--fix"]),
        ]
    for label, cmd in steps:
        if not _run(label, *cmd, *forwarded):
            sys.exit(1)


def lint_cmd(forwarded: Sequence[str] = ()) -> None:
    """Type-check code with mypy. ``forwarded`` args are appended to mypy."""
    if not _run("mypy", "uv", "run", "mypy", "./", *forwarded):
        sys.exit(1)


def test_cmd(forwarded: Sequence[str] = ()) -> None:
    """Run the test suite (requires .env file).

    ``forwarded`` args are appended to the unittest invocation.
    """
    if not _run(
        "tests",
        "uv",
        "run",
        # "--env-file",
        # ".env",
        "python",
        "-m",
        "unittest",
        "discover",
        *forwarded,
    ):
        sys.exit(1)


def all_cmd() -> None:
    """Run format, lint, and test in sequence. Stops on first failure."""
    _rule("Running all tasks")
    format_cmd(nofix=False)
    lint_cmd()
    test_cmd()
    print("All tasks passed")


def main(argv: Sequence[str] | None = None) -> None:
    args_list = list(sys.argv[1:] if argv is None else argv)

    # Split off anything after ``--`` to forward raw to the underlying tool.
    forwarded: list[str] = []
    if "--" in args_list:
        separator = args_list.index("--")
        forwarded = args_list[separator + 1 :]
        args_list = args_list[:separator]

    parser = argparse.ArgumentParser(
        prog="runner.py",
        description="config-db developer task runner.",
        epilog="Arguments after `--` are forwarded to the underlying tool "
        "(not supported for `all`).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    format_parser = subparsers.add_parser("format", help="Format and lint with ruff.")
    format_parser.add_argument(
        "--nofix",
        action="store_true",
        help="Check only; fail instead of modifying files (for CI / hooks).",
    )
    subparsers.add_parser("lint", help="Type-check code with mypy.")
    subparsers.add_parser("test", help="Run the test suite.")
    subparsers.add_parser("all", help="Run format, lint, and test in sequence.")

    args = parser.parse_args(args_list)

    match args.command:
        case "format":
            format_cmd(nofix=args.nofix, forwarded=forwarded)
        case "lint":
            lint_cmd(forwarded)
        case "test":
            test_cmd(forwarded)
        case "all":
            if forwarded:
                parser.error("`all` does not accept forwarded arguments after `--`")
            all_cmd()


if __name__ == "__main__":
    main()
