# Data Quality Report

**Source:** messy_orders.csv
**Generated:** 2026-10-17 05:45 UTC

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

## Analysis settings

- IQR multiplier: 1.5
- Minimum outlier sample size: 4

## Column profile

| Column | Type | Missing | Unique | Mixed | Invalid dates | Outliers | Issues |
|---|---|---:|---:|---:|---:|---:|---|
| order_id | integer | 0 (0.00%) | 11 | 0 | 0 | 0 | none |
| order_date | text | 0 (0.00%) | 11 | 0 | 1 | 0 | invalid date values |
| customer_id | text | 1 (8.33%) | 10 | 0 | 0 | 0 | missing values |
| region | text | 0 (0.00%) | 4 | 0 | 0 | 0 | none |
| quantity | integer | 0 (0.00%) | 4 | 0 | 0 | 1 | potential outliers |
| unit_price | float | 0 (0.00%) | 10 | 0 | 0 | 3 | potential outliers |
| freight_cost | text | 1 (8.33%) | 9 | 1 | 0 | 0 | missing values, mixed numeric/text |
| status | text | 0 (0.00%) | 3 | 0 | 0 | 0 | none |

## Recommendations

- Review duplicate rows before aggregating or counting records.
- Review missing values by column before deciding whether to impute, exclude, or preserve them.
- Keep mixed numeric/text source values separate from any cleaned numeric field instead of coercing text to zero.
- Inspect invalid date values before calculating durations or time-based KPIs.
- Investigate outliers before removing them; unusual values may be valid business events.

## Notes

The checks in this report are screening rules, not automatic cleaning instructions. Business context should decide what gets changed.
