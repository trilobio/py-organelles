# Deploying `runner.py` to a repository

> **Note:** This document was fully written by Claude.

`py_organelles.Runner` is a reusable developer task-runner. It wraps the standard format,
lint, and test commands used by most Trilobio python projects behind a small
[`plac`](https://plac.readthedocs.io/) interpreter with [`rich`](https://rich.readthedocs.io/)-formatted
output. Each repository using `Runner` ships a thin, repo-agnostic `runner.py` at its top level
that simply instantiates `Runner` and hands off to it.

The four sub-commands are:

| Command  | Runs                                                                     |
| -------- | ------------------------------------------------------------------------ |
| `format` | `uv run ruff format ./` then `uv run ruff check [--fix] ./`              |
| `lint`   | `uv run mypy ./`                                                         |
| `test`   | `uv run python -m unittest discover`                                     |
| `all`    | `format` (with `--fix=false`), then `lint`, then `test`                  |
| `help`   | show the help menu, or detailed help for a single command                |

`all` is intended for a commit-hook: it runs every check and exits with a
non-zero status code if any step fails.

A help menu is available via `help`, `-h`, or `--help`, optionally followed by a
command name for detailed help (e.g. `runner.py help format`).

## 1. Add `py-organelles` as a dependency

Make sure the project depends on `py-organelles` (which now pulls in `rich` and
`plac` transitively). In `pyproject.toml`:

```toml
[project]
dependencies = [
    # ...
    "py-organelles",
]

[tool.uv.sources]
py-organelles = { git = "ssh://git@github.com/trilobio/py-organelles.git", rev = "v1.4.0" }
# Or, for local development:
# py-organelles = { path = "../py-organelles", editable = true }
```

Then sync the environment:

```bash
uv sync
```

## 2. Drop `runner.py` into the repository root

Create `runner.py` at the top level of the repository and paste in the script
below.

```python
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
```

That is the entire script. `Runner.main()` reads `sys.argv`: given a command it
runs once and exits with the command's status code (batch mode), and given no
arguments it starts an interactive session.

## 3. Use it

Run a single check (batch mode):

```bash
uv run python runner.py format            # format + ruff check --fix
uv run python runner.py format --fix=false  # format + ruff check (no auto-fix)
uv run python runner.py lint
uv run python runner.py test
uv run python runner.py all               # everything; non-zero exit on failure
uv run python runner.py help              # show the help menu
uv run python runner.py help format       # detailed help for one command
```

Start an interactive session (no arguments):

```bash
$ uv run python runner.py
Developer task runner. Commands: format, lint, test, all, help. Type 'help' for details, or press Ctrl-D to exit.
runner> help
runner> format
runner> all
runner>           # Ctrl-D to exit
```

## 4. Wire `all` into a commit-hook

Because `all` exits non-zero when any check fails, it drops straight into a git
hook. Create `.git/hooks/pre-commit` (and `chmod +x` it):

```bash
#!/usr/bin/env bash
set -euo pipefail
exec uv run python runner.py all
```

## Customisation

`Runner.main()` accepts optional arguments if a repository needs to deviate from
the defaults:

```python
from py_organelles import Runner

if __name__ == "__main__":
    # Run the commands against a sub-directory instead of the repo root.
    Runner.main(path="src")
```

For deeper changes, subclass `Runner` and override individual sub-commands or add
new ones (extend the class-level `commands` list so `plac` and the interactive
session pick them up):

```python
from py_organelles import Runner


class ProjectRunner(Runner):
    commands = [*Runner.commands, "docs"]

    def docs(self) -> None:
        """Build the project documentation."""
        self._run_command(["uv", "run", "mkdocs", "build"])


if __name__ == "__main__":
    ProjectRunner.main()
```

Catch `py_organelles.CommandError` if you need to handle a failing sub-process
programmatically rather than letting it propagate to a non-zero exit code.
