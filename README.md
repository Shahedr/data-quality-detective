# Data Quality Detective

[![tests](https://github.com/Shahedr/data-quality-detective/actions/workflows/tests.yml/badge.svg)](https://github.com/Shahedr/data-quality-detective/actions/workflows/tests.yml) [![PyPI](https://img.shields.io/pypi/v/dqdetect.svg)](https://pypi.org/project/dqdetect/) ![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue) ![MIT License](https://img.shields.io/badge/license-MIT-green)

A lightweight Python CLI for the first pass through a new dataset.

**dqdetect** profiles CSV, Excel, and optional database-table input, flags common data-quality issues, and writes reports that can be reviewed by a person or consumed by another tool. It deliberately does **not** modify the source data.

![Data Quality Detective demo](assets/dqdetect-demo-v010.svg)

## Install

~~~bash
pip install dqdetect
~~~

Profile a file:

~~~bash
dqdetect path/to/file.csv
~~~

By default, dqdetect writes Markdown and HTML reports to the **reports/** folder.

## What it checks

- dataset shape and column types
- duplicate rows
- missing values by column
- constant columns
- mixed numeric/text values
- invalid values in date-like columns
- IQR-based numeric outliers
- optional expected-column and type rules from a JSON schema file

The current scope is intentionally diagnostic: dqdetect tells you what deserves review, but it does not automatically delete, impute, coerce, or replace source values.

## Report formats

Generate one format:

~~~bash
dqdetect data.csv --format md
dqdetect data.csv --format html
dqdetect data.csv --format json
~~~

Generate all three:

~~~bash
dqdetect data.csv --format all
~~~

JSON output includes the dataset summary, analysis settings, per-column profile, optional schema/comparison results, and recommendations.

## Excel

Select an Excel sheet by name or zero-based index:

~~~bash
dqdetect workbook.xlsx --sheet Orders
dqdetect workbook.xlsx --sheet 0
~~~

## Configurable outlier thresholds

The default IQR rule uses a **1.5** multiplier and requires at least **4** non-missing values.

~~~bash
dqdetect data.csv --iqr-multiplier 2.0
dqdetect data.csv --min-outlier-sample-size 10
~~~

These options change how potential numeric outliers are screened; they do not remove any values.

## Schema rules

Use a small JSON file when a dataset is expected to contain specific columns or broad data types.

~~~json
{
  "required_columns": ["order_id", "order_date", "amount"],
  "column_types": {
    "order_id": "numeric",
    "order_date": "date",
    "amount": "numeric"
  },
  "allow_extra_columns": true
}
~~~

Supported schema types are:

- `numeric`
- `text`
- `date`
- `boolean`

Run the schema check with:

~~~bash
dqdetect data.csv --schema schema.json --format all
~~~

See [examples/messy_orders_schema.json](examples/messy_orders_schema.json) for a complete example.

## Compare two versions of a dataset

Compare the current file with an earlier CSV or Excel file:

~~~bash
dqdetect current.csv --compare previous.csv --format all
~~~

The comparison reports:

- row and column count changes
- duplicate-row changes
- added and removed columns
- data-type changes
- missing-value count changes

For Excel comparison files, use `--compare-sheet` when needed.

## Database tables

Database support is optional so the base package stays small.

Install the database extra:

~~~bash
pip install "dqdetect[database]"
~~~

For PostgreSQL, prefer putting the connection URL in an environment variable instead of typing credentials directly into shell history:

~~~bash
export DQDETECT_DATABASE_URL="postgresql+psycopg://user:password@host:5432/database"
dqdetect --table orders --db-schema public --format html
~~~

A SQLAlchemy URL can also be passed with `--database-url`.

The database loader uses SQLAlchemy table reflection rather than constructing a raw SQL string from the table name.

## Use dqdetect in CI

`--fail-on-issues` returns a non-zero exit status when dqdetect finds a data-quality or schema issue.

~~~bash
dqdetect data.csv --schema schema.json --fail-on-issues
~~~

The repository also includes a reusable composite GitHub Action:

~~~yaml
- uses: actions/checkout@v5

- uses: Shahedr/data-quality-detective@v1.0.0
  with:
    file: data/orders.csv
    format: json
    output: dqdetect-reports
    schema: data/schema.json
    fail-on-issues: "true"

- uses: actions/upload-artifact@v4
  if: always()
  with:
    name: dqdetect-report
    path: dqdetect-reports/
~~~

This makes it possible to use the same checks locally and in a repository workflow.

## Example

For the sample dataset in this repository:

~~~text
Data Quality Detective
Source: messy_orders.csv

Rows: 12
Columns: 8
Duplicate rows: 1

Issues found
- 2 columns contain missing values
- 1 column contains mixed numeric/text values
- 1 date-like column contains invalid values
- 2 numeric columns contain potential IQR outliers
~~~

See:

- [examples/messy_orders.csv](examples/messy_orders.csv)
- [examples/messy_orders_report.md](examples/messy_orders_report.md)
- [examples/messy_orders_report.json](examples/messy_orders_report.json)
- [examples/messy_orders_previous.csv](examples/messy_orders_previous.csv)
- [examples/messy_orders_schema.json](examples/messy_orders_schema.json)

## Why the tool does not auto-clean

A suspicious value is not automatically a wrong value.

A freight field containing text such as `Included` may carry business meaning. An extreme order value may be a legitimate large transaction. A missing value may need imputation, exclusion, preservation, or a source-system correction depending on context.

dqdetect therefore follows one rule throughout the project:

**detect → report → review → decide**

## Project structure

~~~text
data-quality-detective/
├── action.yml
├── dqdetect/
│   ├── __init__.py
│   ├── __main__.py
│   ├── checks.py
│   ├── cli.py
│   ├── compare.py
│   ├── database.py
│   ├── io.py
│   ├── profiler.py
│   ├── report.py
│   └── schema.py
├── examples/
├── tests/
├── .github/workflows/
│   ├── tests.yml
│   └── publish-to-pypi.yml
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
└── pyproject.toml
~~~

The package separates command-line handling, input loading, profiling, detection rules, schema validation, comparison, database access, and report generation so each part can be tested independently.

## Testing

The automated test suite covers the CLI, file loading, profiling rules, reporting, schema validation, dataset comparison, database loading, and deterministic IQR behavior.

GitHub Actions runs the tests across Python **3.10–3.13**, performs a real PostgreSQL integration check, smoke-tests the reusable GitHub Action, builds the package, and validates distribution metadata.

Run the suite locally with:

~~~bash
git clone https://github.com/Shahedr/data-quality-detective.git
cd data-quality-detective
pip install -e ".[dev,database]"
pytest
~~~

## Project status

**v1.0.0 completes the planned feature scope for Data Quality Detective.**

The project is feature-complete for its current purpose: a lightweight first-pass profiler. Future changes are expected to be maintenance, bug fixes, compatibility updates, or narrowly scoped improvements rather than continued expansion into a full validation framework.

## License

MIT
