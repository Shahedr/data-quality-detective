# Data Quality Detective v1.0.0

v1.0.0 completes the planned feature scope for Data Quality Detective.

The project remains focused on one job: giving analysts a quick, repeatable first pass through a dataset without automatically changing the source data.

## Highlights

- CSV and Excel profiling
- optional PostgreSQL/database-table profiling
- Markdown, HTML, and JSON reports
- duplicate, missing-value, constant-column, mixed numeric/text, invalid-date, and IQR outlier checks
- configurable IQR thresholds
- JSON schema rules for expected columns and broad types
- comparison between two versions of a dataset
- richer HTML issue overview
- non-zero CI exit mode with `--fail-on-issues`
- reusable GitHub Action
- automated tests across Python 3.10–3.13
- PostgreSQL integration testing
- automated package build, validation, and Trusted Publishing to PyPI

Install:

~~~bash
pip install dqdetect
~~~

Database support:

~~~bash
pip install "dqdetect[database]"
~~~

The tool intentionally reports suspicious data rather than cleaning it automatically. Business context still decides what should be changed.
