# Contributing

Small, focused improvements are welcome.

Useful contributions include:

- a new data-quality check with a clear reason for including it
- tests for an existing check
- support for an additional tabular file format
- clearer error messages
- documentation or example improvements

## Local setup

1. Fork or clone the repository.
2. Create a virtual environment.
3. Install the development dependencies with:

    pip install -e ".[dev]"

4. Run the test suite:

    pytest

## Pull requests

Please keep pull requests focused on one change where possible.

For a new check, include:

- what problem the check is meant to catch
- how false positives are limited
- at least one test
- any README change needed to explain the behavior

The project intentionally flags suspicious data instead of automatically modifying source values. New checks should follow that same principle.
