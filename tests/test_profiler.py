import pandas as pd

from dqdetect.profiler import profile_dataframe


def test_profile_flags_common_issues():
    df = pd.DataFrame(
        {
            "order_date": ["2025-01-01", "bad-date", "2025-01-03", "2025-01-03"],
            "amount": [10.0, 11.0, 12.0, 500.0],
            "freight": ["5.00", "Included", "7.00", "7.00"],
            "customer": ["A", "B", None, None],
        }
    )

    profile = profile_dataframe(df)
    summary = profile["summary"]

    assert summary["columns_with_missing"] == 1
    assert summary["mixed_numeric_text_columns"] == 1
    assert summary["date_columns_with_invalid_values"] == 1
    assert summary["numeric_columns_with_outliers"] == 1


def test_duplicate_rows_are_counted():
    df = pd.DataFrame(
        {
            "id": [1, 2, 2],
            "value": ["a", "b", "b"],
        }
    )

    profile = profile_dataframe(df)

    assert profile["summary"]["duplicate_rows"] == 1


def test_iqr_rule_is_stable_for_sample_values():
    df = pd.DataFrame(
        {
            "unit_price": [
                39.99,
                24.50,
                19.00,
                15.00,
                999.00,
                22.00,
                18.00,
                20.00,
                21.00,
                20.00,
                20.50,
                20.50,
            ]
        }
    )

    profile = profile_dataframe(df)
    column = profile["columns"][0]

    assert column["outlier_count"] == 3
