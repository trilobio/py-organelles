"""Unit tests for the py_organelles.core.runner submodule.

.. note:: This file was fully written by Claude.
"""

import subprocess
import unittest
from io import StringIO
from unittest import mock

from plac_ext import raise_  # type: ignore [import-untyped]
from rich.console import Console

from py_organelles import CommandError, Runner
from py_organelles.core.runner import _str_to_bool


def _make_runner() -> Runner:
    """Build a Runner whose console writes to an in-memory buffer."""
    console = Console(file=StringIO(), highlight=False, force_terminal=False)
    return Runner(path=".", console=console)


class TestStrToBool(unittest.TestCase):
    """Unittests for the _str_to_bool helper."""

    def test_truthy_strings(self) -> None:
        for value in ("true", "TRUE", " t ", "yes", "y", "1"):
            with self.subTest(value=value):
                self.assertTrue(_str_to_bool(value))

    def test_falsy_strings(self) -> None:
        for value in ("false", "FALSE", " f ", "no", "n", "0"):
            with self.subTest(value=value):
                self.assertFalse(_str_to_bool(value))

    def test_passthrough_bool(self) -> None:
        self.assertTrue(_str_to_bool(True))
        self.assertFalse(_str_to_bool(False))

    def test_invalid_string(self) -> None:
        with self.assertRaises(ValueError):
            _str_to_bool("maybe")


class TestCommandError(unittest.TestCase):
    """Unittests for CommandError, including plac's single-argument reconstruction.

    :note: Claude wrote this unittest in response to a bug where plac's re-raising of CommandError
    via ``etype(instance)`` crashed because the constructor required two positional arguments. This
    unittest ensures that CommandError can be constructed and reconstructed from an existing
    instance without crashing, and that it behaves correctly when given a single string argument.
    """

    def test_basic_construction(self) -> None:
        err = CommandError(["uv", "run", "mypy", "./"], returncode=2)
        self.assertEqual(err.command, ["uv", "run", "mypy", "./"])
        self.assertEqual(err.returncode, 2)

    def test_reconstruct_from_instance(self) -> None:
        """plac re-raises via ``etype(existing_instance)``; that must not crash."""
        original = CommandError(["uv", "run", "mypy", "./"], returncode=3)
        rebuilt = CommandError(original)
        self.assertEqual(rebuilt.command, ["uv", "run", "mypy", "./"])
        self.assertEqual(rebuilt.returncode, 3)

    def test_single_string_argument(self) -> None:
        err = CommandError("some message")
        self.assertEqual(err.returncode, 1)
        self.assertIn("some message", str(err))

    def test_placs_raise_helper_roundtrips(self) -> None:
        """Exercise the exact reconstruction path plac.execute() uses."""

        original = CommandError(["uv", "run", "mypy", "./"], returncode=5)
        with self.assertRaises(CommandError) as ctx:
            raise_(type(original), original, None)
        self.assertEqual(ctx.exception.command, ["uv", "run", "mypy", "./"])
        self.assertEqual(ctx.exception.returncode, 5)


class TestRunnerCommands(unittest.TestCase):
    """Unittests for the Runner sub-commands and their wrapped sub-processes."""

    def _patch_run(self, returncodes: list[int]) -> mock._patch[mock.MagicMock]:
        """Patch subprocess.run to return the given sequence of exit codes."""
        results = [mock.Mock(returncode=rc) for rc in returncodes]
        return mock.patch.object(subprocess, "run", side_effect=results)

    def test_format_with_fix(self) -> None:
        runner = _make_runner()
        with self._patch_run([0, 0]) as run:
            runner.format(fix=True)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[0], ["uv", "run", "ruff", "format", "./"])
        self.assertEqual(commands[1], ["uv", "run", "ruff", "check", "--fix", "./"])

    def test_format_without_fix(self) -> None:
        runner = _make_runner()
        with self._patch_run([0, 0]) as run:
            runner.format(fix=False)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[1], ["uv", "run", "ruff", "check", "./"])

    def test_lint_command(self) -> None:
        runner = _make_runner()
        with self._patch_run([0]) as run:
            runner.lint()
        self.assertEqual(run.call_args_list[0].args[0], ["uv", "run", "mypy", "./"])

    def test_test_command(self) -> None:
        runner = _make_runner()
        with self._patch_run([0]) as run:
            runner.test()
        self.assertEqual(
            run.call_args_list[0].args[0],
            ["uv", "run", "python", "-m", "unittest", "discover"],
        )

    def test_run_command_raises_on_failure(self) -> None:
        runner = _make_runner()
        with self._patch_run([1]):
            with self.assertRaises(CommandError) as ctx:
                runner.lint()
        self.assertEqual(ctx.exception.returncode, 1)

    def test_run_command_missing_executable(self) -> None:
        runner = _make_runner()
        with mock.patch.object(subprocess, "run", side_effect=FileNotFoundError("no uv")):
            with self.assertRaises(CommandError) as ctx:
                runner.lint()
        self.assertEqual(ctx.exception.returncode, 127)

    def test_all_runs_format_lint_test_in_order(self) -> None:
        runner = _make_runner()
        with self._patch_run([0, 0, 0, 0]) as run:
            runner.all()
        commands = [call.args[0] for call in run.call_args_list]
        # format (no --fix), then lint, then test.
        self.assertEqual(commands[0], ["uv", "run", "ruff", "format", "--check", "./"])
        self.assertEqual(commands[1], ["uv", "run", "ruff", "check", "./"])
        self.assertEqual(commands[2], ["uv", "run", "mypy", "./"])
        self.assertEqual(commands[3], ["uv", "run", "python", "-m", "unittest", "discover"])

    def test_all_stops_and_errors_on_first_failure(self) -> None:
        runner = _make_runner()
        # ruff format ok, ruff check fails -> lint/test must never run.
        with self._patch_run([0, 1]) as run:
            with self.assertRaises(CommandError):
                runner.all()
        self.assertEqual(run.call_count, 2)


class TestRunnerBatch(unittest.TestCase):
    """Unittests for the batch entry point, including plac argument parsing."""

    def _patch_run(self, returncodes: list[int]) -> mock._patch[mock.MagicMock]:
        results = [mock.Mock(returncode=rc) for rc in returncodes]
        return mock.patch.object(subprocess, "run", side_effect=results)

    def test_batch_success_returns_zero(self) -> None:
        runner = _make_runner()
        with self._patch_run([0]):
            self.assertEqual(runner.run_batch(["lint"]), 0)

    def test_batch_failure_returns_one(self) -> None:
        runner = _make_runner()
        with self._patch_run([1]):
            self.assertEqual(runner.run_batch(["lint"]), 1)

    def test_batch_parses_fix_false_flag(self) -> None:
        runner = _make_runner()
        with self._patch_run([0, 0]) as run:
            self.assertEqual(runner.run_batch(["format", "--fix=false"]), 0)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[1], ["uv", "run", "ruff", "check", "./"])

    def test_batch_parses_fix_true_default(self) -> None:
        runner = _make_runner()
        with self._patch_run([0, 0]) as run:
            self.assertEqual(runner.run_batch(["format"]), 0)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[1], ["uv", "run", "ruff", "check", "--fix", "./"])

    def test_batch_unknown_command_returns_one(self) -> None:
        runner = _make_runner()
        with self._patch_run([]):
            self.assertEqual(runner.run_batch(["bogus"]), 1)

    def test_help_command_runs_no_subprocess(self) -> None:
        for argv in (["help"], ["-h"], ["--help"], ["help", "format"]):
            with self.subTest(argv=argv):
                runner = _make_runner()
                with mock.patch.object(
                    subprocess, "run", side_effect=AssertionError("must not run")
                ) as run:
                    self.assertEqual(runner.run_batch(argv), 0)
                    self.assertEqual(run.call_count, 0)

    def test_help_for_unknown_command_returns_one(self) -> None:
        runner = _make_runner()
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("must not run")):
            self.assertEqual(runner.run_batch(["help", "bogus"]), 1)

    def test_help_in_commands(self) -> None:
        self.assertIn("help", Runner.commands)

    def test_failing_command_reports_cleanly_through_plac(self) -> None:
        """A failing command must surface as a clean exit 1, not a plac TypeError.

        Regression for plac re-raising CommandError via ``etype(instance)``, which
        crashed when the constructor required two positional arguments.
        """
        buf = StringIO()
        runner = Runner(path=".", console=Console(file=buf, highlight=False, width=80))
        with mock.patch.object(subprocess, "run", return_value=mock.Mock(returncode=1)):
            self.assertEqual(runner.run_batch(["lint"]), 1)
        output = buf.getvalue()
        self.assertIn("uv run mypy ./ (exit 1)", output)
        self.assertNotIn("TypeError", output)


if __name__ == "__main__":
    unittest.main()
