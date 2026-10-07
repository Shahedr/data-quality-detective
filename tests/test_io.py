import pandas as pd
import pytest

from dqdetect.io import load_data


def test_load_csv(tmp_path):
    path = tmp_path / "sample.csv"
    pd.DataFrame({"id": [1, 2]}).to_csv(path, index=False)

    df = load_data(path)

    assert df["id"].tolist() == [1, 2]


def test_rejects_unsupported_file_type(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("id\n1\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_data(path)
