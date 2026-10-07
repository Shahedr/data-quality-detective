from pathlib import Path

import pandas as pd

from dqdetect.checks import (
    invalid_date_count,
    iqr_outlier_count,
    mixed_numeric_text_count,
)


def _sample_values(series, limit=3):
    values = series.dropna().astype(str).drop_duplicates().head(limit)
    return [value[:60] for value in values]


def profile_dataframe(df, source_name="dataset"):
    row_count, column_count = df.shape
    duplicate_rows = int(df.duplicated().sum())

    columns = []

    for column in df.columns:
        series = df[column]
        missing_count = int(series.isna().sum())
        unique_count = int(series.nunique(dropna=True))
        mixed_count = mixed_numeric_text_count(series)
        invalid_dates = invalid_date_count(series, column)
        outliers = iqr_outlier_count(series)
        is_constant = unique_count <= 1

        issues = []
        if missing_count:
            issues.append("missing values")
        if is_constant:
            issues.append("constant column")
        if mixed_count:
            issues.append("mixed numeric/text")
        if invalid_dates:
            issues.append("invalid date values")
        if outliers:
            issues.append("potential outliers")

        columns.append(
            {
                "column": str(column),
                "dtype": str(series.dtype),
                "missing_count": missing_count,
                "missing_pct": round(
                    (missing_count / row_count * 100) if row_count else 0.0,
                    2,
                ),
                "unique_count": unique_count,
                "constant": is_constant,
                "mixed_numeric_text_count": mixed_count,
                "invalid_date_count": invalid_dates,
                "outlier_count": outliers,
                "sample_values": _sample_values(series),
                "issues": issues,
            }
        )

    summary = {
        "source": Path(source_name).name,
        "rows": row_count,
        "columns": column_count,
        "duplicate_rows": duplicate_rows,
        "columns_with_missing": sum(
            item["missing_count"] > 0 for item in columns
        ),
        "constant_columns": sum(item["constant"] for item in columns),
        "mixed_numeric_text_columns": sum(
            item["mixed_numeric_text_count"] > 0 for item in columns
        ),
        "date_columns_with_invalid_values": sum(
            item["invalid_date_count"] > 0 for item in columns
        ),
        "numeric_columns_with_outliers": sum(
            item["outlier_count"] > 0 for item in columns
        ),
    }

    return {
        "summary": summary,
        "columns": columns,
    }
