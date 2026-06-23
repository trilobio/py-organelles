"""Reusable developer task-runner TUI shared across Trilobio python repositories.

This module exposes :class:`Runner`, a small `plac.Interpreter`-driven command line
tool that wraps the formatting, linting and testing commands every project runs.
It is intentionally repository-agnostic: each repo ships a thin ``runner.py`` at its
top level that instantiates :class:`Runner` and calls :meth:`Runner.main`.

The sub-commands are:

* ``format`` -- ``uv run ruff format ./`` then ``uv run ruff check [--fix] ./``
* ``lint``   -- ``uv run mypy ./``
* ``test``   -- ``uv run python -m unittest discover``
* ``all``    -- ``format`` (with ``--fix=false``), then ``lint``, then ``test``
* ``help``   -- show the help menu, or detailed help for a single command

``all`` is intended for use in a git commit-hook: it runs every check and exits with
a non-zero status code if any underlying command fails. Passing ``help``, ``-h`` or
``--help`` (optionally followed by a command name) prints a help menu.

.. note:: This file was fully written by Claude.
"""

from __future__ import annotations

import inspect
import pathlib
import shlex
import subprocess
import sys
from io import StringIO
from typing import Sequence

import plac  # type: ignore [import-untyped]
from rich.console import Console
from rich.markup import escape as markup_escape
from rich.table import Table

_TRUE_STRINGS = frozenset({"true", "t", "yes", "y", "1"})
_FALSE_STRINGS = frozenset({"false", "f", "no", "n", "0"})


class CommandError(RuntimeError):
    """Raised when a wrapped sub-process exits with a non-zero status code.

    :param command: The command (as an argv list) that failed. When a
        :class:`CommandError` instance is passed instead, its attributes are
        copied — see the note below.
    :param returncode: The non-zero exit status returned by the command.

    .. note:: ``returncode`` is optional and the constructor accepts a single
        argument so that :func:`plac_ext.raise_` can re-raise this exception.
        When ``plac`` re-raises a task's error it does ``etype(existing_instance)``
        (a single-argument call), so an exception that *requires* two positional
        arguments would crash with a confusing ``TypeError`` deep inside plac.
        Supporting the single-argument form (and copying state when handed an
        existing instance) keeps re-raising faithful and crash-free.
    """

    def __init__(
        self,
        command: str | Sequence[str] | CommandError,
        returncode: int | None = None,
    ) -> None:
        if isinstance(command, CommandError):
            # plac re-raises via ``etype(existing_instance)``; copy the originals.
            command, returncode = command.command, command.returncode  # type: ignore [attr-defined]
        if isinstance(command, str):
            # Support a single string argument for plac's re-raise helper.
            command = [command]
        self.command: Sequence[str] = command
        self.returncode = 1 if returncode is None else returncode
        super().__init__(
            f"Command {shlex.join(command)!r} failed with exit code {self.returncode}."
        )


def _str_to_bool(value: str | bool) -> bool:
    """Convert a command-line string such as ``"false"`` to a boolean.

    :param value: The raw string (or already-coerced bool) to interpret.
    :return: The corresponding boolean value.
    :raises ValueError: if *value* cannot be interpreted as a boolean.
    """
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in _TRUE_STRINGS:
        return True
    if normalized in _FALSE_STRINGS:
        return False
    raise ValueError(f"Cannot interpret {value!r} as a boolean (use true/false, yes/no, or 1/0).")


def _render_prompt(markup: str) -> str:
    """Render a rich markup string to an ANSI-escaped string for use with ``input()``.

    :param markup: The rich-markup prompt string to render.
    :return: An ANSI string with readline-safe non-printing markers.
    """
    import re  # noqa: PLC0415

    buf: StringIO = StringIO()  # Explicit annotation; prevents Console-internal type widening.
    console = Console(file=buf, force_terminal=True, highlight=False, color_system="256")
    console.print(markup, end="")
    # Wrap escape codes in \001..\002 so readline doesn't miscount the prompt width.
    return re.sub(r"(\x1b\[[0-9;]*m)", r"\001\1\002", buf.getvalue())


class Runner:
    """Interactive task-runner exposing ``format``, ``lint``, ``test``, ``all`` and ``help``.

    The class is designed to be driven by :class:`plac.Interpreter`; each public method
    is a sub-command. Instantiate it and call :meth:`main` from a repository's top-level
    ``runner.py`` to get both a batch interface (for commit-hooks/CI) and an interactive
    session.

    :param path: The directory the wrapped commands operate on (defaults to the current
        working directory).
    :param console: An optional pre-configured rich :class:`~rich.console.Console`.
    """

    # ``plac.Interpreter`` replaces the instance's ``commands`` with an unordered set at
    # runtime, so keep a separate ordered copy for help rendering and usage messages.
    _ORDERED_COMMANDS = ("format", "lint", "test", "all", "help")
    commands = list(_ORDERED_COMMANDS)

    def __init__(
        self,
        path: str | pathlib.Path = ".",
        console: Console | None = None,
    ) -> None:
        self._path = pathlib.Path(path)
        self._console = console if console is not None else Console(highlight=False)

    # ── Internal helpers ─────────────────────────────────────────

    def _run_command(self, command: list[str]) -> None:
        """Run *command* in :attr:`_path`, streaming its output to the terminal.

        :param command: The command to run, as an argv list.
        :raises CommandError: if the command exits with a non-zero status code, or if
            the executable cannot be found.
        """
        pretty = shlex.join(command)
        self._console.rule(f"[bold blue]{markup_escape(pretty)}")
        try:
            result = subprocess.run(command, cwd=self._path)
        except FileNotFoundError as err:
            self._console.print(
                f"[red]✗ Could not run {markup_escape(pretty)}: {markup_escape(str(err))}[/red]"
            )
            raise CommandError(command, returncode=127) from err

        if result.returncode != 0:
            self._console.print(f"[red]✗ {markup_escape(pretty)} (exit {result.returncode})[/red]")
            raise CommandError(command, returncode=result.returncode)

        self._console.print(f"[green]✓ {markup_escape(pretty)}[/green]")

    # ── Sub-commands ─────────────────────────────────────────────

    @plac.annotations(
        fix=plac.Annotation(
            "Pass --fix to 'ruff check' to auto-fix lint errors (default: true).",
            "option",
            "f",
            _str_to_bool,
        ),
    )
    def format(self, fix: bool = True) -> None:
        """Format the codebase with ruff and (optionally) auto-fix lint errors.

        Runs ``uv run ruff format ./`` followed by ``uv run ruff check ./``; when
        *fix* is true the ``--fix`` flag is added so ruff repairs what it can.

        :param fix: Whether to pass ``--fix`` to ``ruff check`` (default: true).
        """
        format_command = ["uv", "run", "ruff", "format"]
        if not fix:
            format_command.append("--check")
        format_command.append("./")
        self._run_command(format_command)
        check_command = ["uv", "run", "ruff", "check"]
        if fix:
            check_command.append("--fix")
        check_command.append("./")
        self._run_command(check_command)

    def lint(self) -> None:
        """Type-check the codebase with ``uv run mypy ./``."""
        self._run_command(["uv", "run", "mypy", "./"])

    def test(self) -> None:
        """Run the test-suite with ``uv run python -m unittest discover``."""
        self._run_command(["uv", "run", "python", "-m", "unittest", "discover"])

    def all(self) -> None:
        """Run every check in order: format (no auto-fix), then lint, then test.

        Intended for use in a commit-hook. ``--fix=false`` is passed to :meth:`format`
        so the working tree is never silently modified; if any step fails a
        :class:`CommandError` propagates so the process exits non-zero.

        :raises CommandError: if any of the format, lint or test commands fail.
        """
        self.format(fix=False)
        self.lint()
        self.test()
        self._console.print("[bold green]✓ All checks passed.[/bold green]")

    @plac.annotations(
        command=plac.Annotation(
            "Optional command to show detailed help for.",
            "positional",
            None,
            str,
        ),
    )
    def help(self, command: str | None = None) -> None:
        """Show the help menu, or detailed help for a single command.

        :param command: When given, print detailed help for that command instead
            of the top-level menu.
        """
        if command is None:
            self._print_help()
        elif command in self.commands:
            self._print_command_help(command)
        else:
            self._console.print(
                f"[red]Unknown command {markup_escape(command)!r}. "
                f"Choose from: {', '.join(self.commands)}.[/red]"
            )

    # ── Help rendering ───────────────────────────────────────────

    def _command_summary(self, command: str) -> str:
        """Return the first line of *command*'s docstring, stripped of rST markup."""
        doc = inspect.getdoc(getattr(self, command)) or ""
        first_line = doc.split("\n", 1)[0].strip()
        return first_line.replace("``", "")

    def _print_help(self) -> None:
        """Print the top-level help menu listing every command."""
        self._console.print("[bold]runner[/bold] — developer task runner\n")

        self._console.print("[bold]Usage:[/bold]")
        usage_rows = [
            ("uv run python runner.py <command> [options]", "run a single command"),
            ("uv run python runner.py", "start an interactive session"),
        ]
        usage_width = max(len(invocation) for invocation, _ in usage_rows)
        for invocation, description in usage_rows:
            self._console.print(f"  {markup_escape(invocation):<{usage_width}}   {description}")
        self._console.print()

        table = Table(show_header=True, header_style="bold blue", box=None, pad_edge=False)
        table.add_column("Command", style="green", no_wrap=True)
        table.add_column("Description")
        for command in self.commands:
            table.add_row(command, markup_escape(self._command_summary(command)))
        self._console.print(table)

        self._console.print("\n[bold]Examples:[/bold]")
        self._console.print("  uv run python runner.py all")
        self._console.print("  uv run python runner.py format --fix=false")
        self._console.print("  uv run python runner.py help format")

    def _print_command_help(self, command: str) -> None:
        """Print the full docstring for a single *command*."""
        doc = inspect.getdoc(getattr(self, command)) or "(no description available)"
        self._console.print(f"[bold green]{markup_escape(command)}[/bold green]\n")
        self._console.print(markup_escape(doc.replace("``", "")))

    # ── Entry points ─────────────────────────────────────────────

    def run_batch(self, argv: list[str]) -> int:
        """Execute a single command from *argv* and return a process exit code.

        :param argv: The command and its arguments (e.g. ``["format", "--fix=false"]``).
        :return: ``0`` on success, ``1`` on failure (including an unknown command).
        """
        if argv and argv[0] in ("-h", "--help", "help"):
            # Render help directly (outside plac) so exit codes stay under our control.
            target = argv[1] if len(argv) > 1 else None
            if target is not None and target not in self.commands:
                self._console.print(
                    f"[red]Error: unknown command {markup_escape(target)!r}. "
                    f"Choose from: {', '.join(self.commands)}.[/red]"
                )
                return 1
            self.help(target)
            return 0
        if not argv or argv[0] not in self.commands:
            given = argv[0] if argv else ""
            self._console.print(
                f"[red]Error: unknown command {markup_escape(given)!r}. "
                f"Choose from: {', '.join(self.commands)}.[/red]"
            )
            return 1
        line = shlex.join(argv)
        try:
            # ``execute`` manages its own ``with self:`` context, so do not wrap it in
            # another one — entering the same Interpreter twice corrupts its teardown.
            plac.Interpreter(self).execute([line], verbose=False)
        except CommandError:
            # _run_command already reported the failing command.
            return 1
        except Exception as err:  # noqa: BLE001 -- surface parse/usage errors cleanly.
            self._console.print(f"[red]Error: {markup_escape(str(err))}[/red]")
            return 1
        return 0

    def run_interactive(self) -> None:
        """Start an interactive plac session, reading commands until EOF/Ctrl-C."""
        prompt = _render_prompt("[blue]runner>[/blue] ")
        self._console.print(
            "[blue]Developer task runner.[/blue] "
            f"Commands: {', '.join(self.commands)}. "
            "Type 'help' for details, or press Ctrl-D to exit."
        )
        # ``interact`` manages its own ``with self:`` context and reports per-command
        # errors inline (it only returns on EOF), so it is called without an extra
        # context wrapper.
        try:
            plac.Interpreter(self).interact(prompt=prompt)
        except (EOFError, KeyboardInterrupt):
            pass

    @classmethod
    def main(
        cls,
        argv: list[str] | None = None,
        path: str | pathlib.Path = ".",
    ) -> None:
        """CLI entry point: run one command (batch) or start an interactive session.

        With arguments, a single command is executed and the process exits with a
        non-zero status code if it fails (suitable for a commit-hook). With no
        arguments, an interactive session is started.

        :param argv: The argument list to use; defaults to ``sys.argv[1:]``.
        :param path: The directory the commands operate on (default: current directory).
        """
        argv = sys.argv[1:] if argv is None else argv
        runner = cls(path=path)
        if argv:
            raise SystemExit(runner.run_batch(argv))
        runner.run_interactive()
