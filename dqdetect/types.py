from pandas.api.types import (
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_string_dtype,
)


def dtype_label(series):
    dtype = series.dtype
    name = str(dtype).lower()
    kind = getattr(dtype, "kind", "")

    if is_bool_dtype(dtype) or kind == "b" or name in {"bool", "boolean"}:
        return "boolean"

    if (
        is_datetime64_any_dtype(dtype)
        or kind == "M"
        or name.startswith("datetime")
    ):
        return "datetime"

    if kind in {"i", "u"} or name.startswith(("int", "uint")):
        return "integer"

    if kind == "f" or name.startswith("float"):
        return "float"

    if is_numeric_dtype(dtype):
        return "numeric"

    if is_string_dtype(dtype) or kind in {"O", "U", "S"}:
        return "text"

    if name in {"object", "string", "str"}:
        return "text"

    return name
