import pandas as pd

from dqdetect.compare import compare_profiles
from dqdetect.profiler import profile_dataframe


def test_compare_profiles_reports_structural_changes():
    previous = profile_dataframe(
        pd.DataFrame(
            {
                "id": [1, 2],
                "amount": [10.0, 20.0],
                "old_column": ["a", "b"],
            }
        ),
        source_name="previous.csv",
    )
    current = profile_dataframe(
        pd.DataFrame(
            {
                "id": [1, 2, 3],
                "amount": ["10", None, "30"],
                "new_column": ["x", "y", "z"],
            }
        ),
        source_name="current.csv",
    )

    comparison = compare_profiles(current, previous)

    assert comparison["row_delta"] == 1
    assert comparison["column_delta"] == 0
    assert comparison["added_columns"] == ["new_column"]
    assert comparison["removed_columns"] == ["old_column"]
    assert comparison["type_changes"][0]["column"] == "amount"
    assert comparison["missing_value_changes"][0]["column"] == "amount"
    assert comparison["missing_value_changes"][0]["delta"] == 1
