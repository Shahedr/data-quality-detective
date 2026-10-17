import pandas as pd
import pytest

from dqdetect.checks import iqr_outlier_count


def test_iqr_multiplier_is_configurable():
    series = pd.Series([10, 10, 11, 11, 12, 12, 30])

    strict_count = iqr_outlier_count(series, multiplier=1.5)
    relaxed_count = iqr_outlier_count(series, multiplier=10.0)

    assert strict_count == 1
    assert relaxed_count == 0


def test_iqr_minimum_sample_size_is_configurable():
    series = pd.Series([1, 1, 1, 100])

    assert iqr_outlier_count(series, min_sample_size=5) == 0


def test_iqr_rejects_invalid_settings():
    series = pd.Series([1, 2, 3, 4])

    with pytest.raises(ValueError):
        iqr_outlier_count(series, multiplier=0)

    with pytest.raises(ValueError):
        iqr_outlier_count(series, min_sample_size=0)
