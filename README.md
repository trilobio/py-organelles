# py-organelles

Small yet vital python tools found in all Trilobio python projects 

## Developer Setup

### Linting, formatting, and unittesting

For all main developer tasks, `runner.py` contains commands to run them.
```
uv run runner.py -h
```

### Pre-commit Hook

To automatically run the linter and checker on the code, run the following command from the repository root directory:
```
ln -sf ../../scripts/hooks/pre-commit .git/hooks/pre-commit
```
