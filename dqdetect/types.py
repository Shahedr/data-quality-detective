from pandas.api.types import (
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_string_dtype,
)


def dtype_label(series):
    dtype = series.dtype
    name = str(dtype).lower()

    if is_bool_dtype(dtype) or name in {"bool", "boolean"}:
        return "boolean"

    if is_datetime64_any_dtype(dtype) or name.startswith("datetime"):
        return "datetime"

    # String checks keep output stable across pandas/NumPy dtype implementations,
    # including nullable integer dtypes such as Int64.
    if name.startswith("int") or name.startswith("uint"):
        return "integer"

    if name.startswith("float"):
        return "float"

    if is_numeric_dtype(dtype):
        return "numeric"

    if is_string_dtype(dtype) or name in {"object", "string", "str"}:
        return "text"

    return name
