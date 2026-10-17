import pandas as pd

from dqdetect.types import dtype_label


def test_dtype_labels_are_semantic_and_stable():
    assert dtype_label(pd.Series([1, 2])) == "integer"
    assert dtype_label(pd.Series([1.5, 2.5])) == "float"
    assert dtype_label(pd.Series(["a", "b"])) == "text"
    assert dtype_label(pd.Series([True, False])) == "boolean"
    assert dtype_label(pd.Series(pd.to_datetime(["2026-01-01"]))) == "datetime"
