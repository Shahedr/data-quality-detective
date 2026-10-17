# Contributing

Data Quality Detective is feature-complete for its current v1 scope. Maintenance contributions and small, focused improvements are still welcome.

Useful contributions include:

- bug fixes
- tests for existing behavior
- compatibility fixes for supported Python or dependency versions
- clearer error messages
- documentation or example corrections
- narrowly scoped data-quality checks that fit the existing first-pass profiler

## Local setup

1. Fork or clone the repository.
2. Create a virtual environment.
3. Install the development and database dependencies:

    pip install -e ".[dev,database]"

4. Run the test suite:

    pytest

## Pull requests

Please keep pull requests focused on one change where possible.

For a new or changed check, include:

- what problem the check is meant to catch
- how false positives are limited
- at least one test
- any README change needed to explain the behavior

The project intentionally flags suspicious data instead of automatically modifying source values. Changes should preserve that principle and should not turn dqdetect into an automatic cleaner or full validation platform.
