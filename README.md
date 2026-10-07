# Data Quality Detective

[![tests](https://github.com/Shahedr/data-quality-detective/actions/workflows/tests.yml/badge.svg)](https://github.com/Shahedr/data-quality-detective/actions/workflows/tests.yml) ![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue) ![MIT License](https://img.shields.io/badge/license-MIT-green)

A small command-line tool for quickly profiling CSV and Excel files before analysis.

I built this around a problem I keep running into in analytics work: a dataset can look usable at first, but the real issues only show up after checking missing values, duplicate rows, mixed numeric/text fields, date parsing, and unusual numeric values.

**dqdetect** puts those checks into one repeatable command and writes a report you can review or share.

## Quick start

~~~bash
git clone https://github.com/Shahedr/data-quality-detective.git
cd data-quality-detective

python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows
# .venv/Scripts/activate

pip install -e .
dqdetect examples/messy_orders.csv
~~~

By default the command writes Markdown and HTML reports to the **reports/** folder. JSON output is available when you want to feed the profile into another script, CI job, or data workflow.

## What it checks

- dataset shape and column types
- duplicate rows
- missing values by column
- constant columns
- mixed numeric/text values
- invalid values in date-like columns
- IQR-based outlier counts for numeric columns
- machine-readable JSON output for automation

The tool does **not** automatically delete or "fix" anything. The report is meant to help an analyst decide what deserves review.

## Example

~~~text
Data Quality Detective
File: examples/messy_orders.csv

Rows: 12
Columns: 8
Duplicate rows: 1

Reports written to:
  reports/messy_orders_report.md
  reports/messy_orders_report.html
~~~

See [examples/messy_orders_report.md](examples/messy_orders_report.md) for a sample report.

## CLI

~~~bash
dqdetect path/to/file.csv
dqdetect workbook.xlsx --sheet Orders
dqdetect workbook.xlsx --sheet 0
dqdetect data.csv --format html
dqdetect data.csv --format json
dqdetect data.csv --format all
dqdetect data.csv --output audit_reports
~~~

Supported formats:

- CSV
- Excel (.xlsx)

## JSON output

Use JSON when the report needs to be consumed by another tool rather than read by a person.

~~~bash
dqdetect data.csv --format json
~~~

The JSON file includes the dataset summary, per-column profile, issue flags, and recommendations. Use `--format all` when you want Markdown, HTML, and JSON from the same run.

## Why these checks?

This first version focuses on issues that can change an analysis if they are handled carelessly.

For example, a freight-cost field containing both dollar values and text such as "included elsewhere" should not simply be converted to zero. Likewise, an extreme numeric value may be a data-entry problem or a legitimate observation. The tool flags these cases instead of making the decision for you.

## Project structure

~~~text
data-quality-detective/
├── dqdetect/
│   ├── __init__.py
│   ├── checks.py
│   ├── cli.py
│   ├── io.py
│   ├── profiler.py
│   └── report.py
├── examples/
│   ├── messy_orders.csv
│   └── messy_orders_report.md
├── tests/
├── .github/workflows/tests.yml
├── CONTRIBUTING.md
├── LICENSE
└── pyproject.toml
~~~

## Development

~~~bash
pip install -e ".[dev]"
pytest
~~~

## Roadmap

Things I would like to add next:

- user-configurable thresholds
- schema rules for expected columns and types
- PostgreSQL table profiling
- comparison between two versions of a dataset
- richer HTML charts
- optional GitHub Action for automated data-quality checks

I am keeping the first release intentionally small so the checks are understandable and easy to extend.

## License

MIT
