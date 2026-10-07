import pandas as pd
from pandas.api.types import is_numeric_dtype


DATE_NAME_HINTS = (
    "date",
    "time",
    "timestamp",
    "created",
    "updated",
    "dob",
)


def is_date_like_column(column_name):
    name = str(column_name).lower()
    return any(hint in name for hint in DATE_NAME_HINTS)


def mixed_numeric_text_count(series):
    if is_numeric_dtype(series):
        return 0

    values = series.dropna().astype(str).str.strip()
    values = values[values.ne("")]

    if values.empty:
        return 0

    parsed = pd.to_numeric(values, errors="coerce")
    numeric_count = int(parsed.notna().sum())
    text_count = int(parsed.isna().sum())

    if numeric_count == 0 or text_count == 0:
        return 0

    return min(numeric_count, text_count)


def invalid_date_count(series, column_name):
    if not is_date_like_column(column_name):
        return 0

    values = series.dropna()
    if values.empty:
        return 0

    parsed = pd.to_datetime(values, errors="coerce")
    return int(parsed.isna().sum())


def iqr_outlier_count(series):
    if not is_numeric_dtype(series):
        return 0

    values = series.dropna()
    if len(values) < 4:
        return 0

    q1 = values.quantile(0.25)
    q3 = values.quantile(0.75)
    iqr = q3 - q1

    if pd.isna(iqr) or iqr == 0:
        return 0

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return int(((values < lower) | (values > upper)).sum())
