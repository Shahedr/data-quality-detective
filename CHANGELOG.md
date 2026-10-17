# Changelog

All notable changes to Data Quality Detective are documented here.

## [1.0.0] - 2026-10-17

This release completes the planned feature scope for the project.

### Added

- machine-readable JSON report output with `--format json`
- `--format all` for Markdown, HTML, and JSON in one run
- configurable IQR multiplier and minimum outlier sample size
- JSON schema rules for required columns and broad expected data types
- comparison between current and previous CSV/Excel datasets
- optional SQLAlchemy database-table profiling with PostgreSQL support
- richer HTML issue overview
- `--fail-on-issues` for CI/data-quality gates
- reusable composite GitHub Action
- PostgreSQL integration coverage in CI
- GitHub Action smoke testing in CI

### Changed

- report payloads now include analysis settings
- Markdown and HTML reports can include schema and comparison results
- package maturity moved from alpha to beta
- CLI input handling now supports either a file or database table

### Design

The project remains a first-pass profiler. It flags suspicious data and schema mismatches without automatically changing source values.

## [0.1.0] - 2026-10-06

First public release.

### Added

- `dqdetect` command-line interface
- CSV and Excel (`.xlsx`) input
- dataset row/column summary
- duplicate-row detection
- missing-value profiling
- constant-column detection
- mixed numeric/text detection
- invalid-value checks for date-like columns
- IQR-based numeric outlier flags
- Markdown report generation
- HTML report generation
- configurable report output directory and format
- Excel sheet selection by name or numeric index
- sample messy-orders dataset and sample report
- pytest test suite
- GitHub Actions testing across Python 3.10–3.13
- package build and metadata validation in CI
- MIT license and contribution guide

### Design choice

The tool flags suspicious data but does not automatically modify source values. Cleaning decisions are intentionally left to the analyst because missing values, text in numeric-looking fields, and statistical outliers can carry legitimate business meaning.
