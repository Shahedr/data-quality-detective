# Changelog

All notable changes to Data Quality Detective are documented here.

## Unreleased

### Added

- machine-readable JSON report output for scripts and CI workflows
- `--format json` for JSON-only output
- `--format all` for Markdown, HTML, and JSON in one run


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
