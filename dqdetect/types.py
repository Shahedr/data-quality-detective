from pandas.api.types import (
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_float_dtype,
    is_integer_dtype,
    is_numeric_dtype,
    is_string_dtype,
)


def dtype_label(series):
    dtype = series.dtype

    if is_bool_dtype(dtype):
        return "boolean"

    if is_datetime64_any_dtype(dtype):
        return "datetime"

    if is_integer_dtype(dtype):
        return "integer"

    if is_float_dtype(dtype):
        return "float"

    if is_numeric_dtype(dtype):
        return "numeric"

    if is_string_dtype(dtype) or str(dtype) in {"object", "string", "str"}:
        return "text"

    return str(dtype)
