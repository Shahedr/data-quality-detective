import json
from pathlib import Path

import pandas as pd
from pandas.api.types import (
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
)


ALLOWED_TYPES = {"numeric", "text", "date", "boolean"}


def load_schema(path):
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Schema file not found: {source}")

    try:
        rules = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid schema JSON: {exc.msg}") from exc

    if not isinstance(rules, dict):
        raise ValueError("Schema must be a JSON object")

    required = rules.get("required_columns", [])
    column_types = rules.get("column_types", {})
    allow_extra = rules.get("allow_extra_columns", True)

    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        raise ValueError("'required_columns' must be a list of column names")

    if not isinstance(column_types, dict):
        raise ValueError("'column_types' must be an object mapping columns to types")

    invalid_types = sorted(
        {str(value).lower() for value in column_types.values()} - ALLOWED_TYPES
    )
    if invalid_types:
        allowed = ", ".join(sorted(ALLOWED_TYPES))
        raise ValueError(
            f"Unsupported schema type(s): {', '.join(invalid_types)}. "
            f"Allowed types: {allowed}"
        )

    if not isinstance(allow_extra, bool):
        raise ValueError("'allow_extra_columns' must be true or false")

    return {
        "required_columns": required,
        "column_types": {
            str(column): str(expected).lower()
            for column, expected in column_types.items()
        },
        "allow_extra_columns": allow_extra,
    }


def _matches_expected_type(series, expected):
    if expected == "numeric":
        return bool(is_numeric_dtype(series))

    if expected == "boolean":
        return bool(is_bool_dtype(series))

    if expected == "date":
        if is_datetime64_any_dtype(series):
            return True
        values = series.dropna()
        if values.empty:
            return True
        parsed = pd.to_datetime(values, errors="coerce")
        return bool(parsed.notna().all())

    if expected == "text":
        return not (
            is_numeric_dtype(series)
            or is_bool_dtype(series)
            or is_datetime64_any_dtype(series)
        )

    return False


def validate_schema(df, rules):
    required = rules.get("required_columns", [])
    column_types = rules.get("column_types", {})
    allow_extra = rules.get("allow_extra_columns", True)

    actual_columns = [str(column) for column in df.columns]
    actual_set = set(actual_columns)

    missing_required = [
        column for column in required if column not in actual_set
    ]

    declared_columns = set(required) | set(column_types)
    unexpected_columns = (
        sorted(actual_set - declared_columns) if not allow_extra else []
    )

    type_mismatches = []
    for column, expected in column_types.items():
        if column not in df.columns:
            continue

        series = df[column]
        if not _matches_expected_type(series, expected):
            type_mismatches.append(
                {
                    "column": column,
                    "expected": expected,
                    "actual": str(series.dtype),
                }
            )

    valid = not (missing_required or unexpected_columns or type_mismatches)

    return {
        "valid": valid,
        "missing_required_columns": missing_required,
        "unexpected_columns": unexpected_columns,
        "type_mismatches": type_mismatches,
    }
