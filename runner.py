#!/usr/bin/env python3
"""Developer task runner.

Wraps the project's formatting, linting and testing commands behind a small
interactive TUI built on :class:`py_organelles.Runner`.

Run a single command (suitable for git hooks / CI)::

    uv run python runner.py all
    uv run python runner.py format --fix=false

Or start an interactive session with no arguments::

    uv run python runner.py
"""

from py_organelles import Runner

if __name__ == "__main__":
    Runner.main()
