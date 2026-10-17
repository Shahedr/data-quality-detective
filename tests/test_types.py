import pandas as pd

from dqdetect.types import dtype_label


def test_dtype_labels_are_semantic_and_stable():
    assert dtype_label(pd.Series([1, 2])) == "integer"
    assert dtype_label(pd.Series([1.5, 2.5])) == "float"
    assert dtype_label(pd.Series(["a", "b"])) == "text"
    assert dtype_label(pd.Series([True, False])) == "boolean"
    assert dtype_label(pd.Series(pd.to_datetime(["2026-01-01"]))) == "datetime"


def test_nullable_dtypes_are_normalized():
    assert dtype_label(pd.Series([1, None], dtype="Int64")) == "integer"
    assert dtype_label(pd.Series(["a", None], dtype="string")) == "text"


def test_csv_integer_dtype_is_normalized(tmp_path):
    from dqdetect.io import load_data
    from dqdetect.profiler import profile_dataframe

    path = tmp_path / "sample.csv"
    path.write_text(
        "id,quantity,price\n1,2,10.5\n2,3,12.5\n",
        encoding="utf-8",
    )

    profile = profile_dataframe(load_data(path))
    dtypes = {item["column"]: item["dtype"] for item in profile["columns"]}

    assert dtypes == {
        "id": "integer",
        "quantity": "integer",
        "price": "float",
    }
