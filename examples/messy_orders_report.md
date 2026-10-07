# Data Quality Report — Sample Output

**Source:** messy_orders.csv

This file is committed as an example of what Data Quality Detective reports from the sample dataset in this repository.

## Dataset summary

| Metric | Value |
|---|---:|
| Rows | 12 |
| Columns | 8 |
| Duplicate rows | 1 |
| Columns with missing values | 2 |
| Constant columns | 0 |
| Mixed numeric/text columns | 1 |
| Date columns with invalid values | 1 |
| Numeric columns with potential outliers | 2 |

## Column profile

| Column | Type | Missing | Unique | Mixed | Invalid dates | Outliers | Issues |
|---|---|---:|---:|---:|---:|---:|---|
| order_id | int64 | 0 (0.00%) | 11 | 0 | 0 | 0 | none |
| order_date | object | 0 (0.00%) | 11 | 0 | 1 | 0 | invalid date values |
| customer_id | object | 1 (8.33%) | 10 | 0 | 0 | 0 | missing values |
| region | object | 0 (0.00%) | 4 | 0 | 0 | 0 | none |
| quantity | int64 | 0 (0.00%) | 4 | 0 | 0 | 1 | potential outliers |
| unit_price | float64 | 0 (0.00%) | 10 | 0 | 0 | 3 | potential outliers |
| freight_cost | object | 1 (8.33%) | 9 | 1 | 0 | 0 | missing values, mixed numeric/text |
| status | object | 0 (0.00%) | 3 | 0 | 0 | 0 | none |

## What I would review first

- Confirm whether the duplicated order row is a true duplicate or a repeated transaction.
- Investigate the invalid value in order_date before doing time-based analysis.
- Keep the text value in freight_cost separate from any numeric freight field instead of converting it to zero.
- Review the unusually large quantity and unit-price observations before deciding whether they are errors.

## Note

IQR outlier flags are screening signals, not proof that a value is wrong. The tool intentionally leaves cleaning decisions to the analyst.
