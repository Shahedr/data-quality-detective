import pandas as pd
import pytest

from dqdetect.io import load_data


def test_load_csv(tmp_path):
    path = tmp_path / "sample.csv"
    pd.DataFrame({"id": [1, 2]}).to_csv(path, index=False)

    df = load_data(path)

    assert df["id"].tolist() == [1, 2]


def test_load_xlsx_by_sheet_index(tmp_path):
    path = tmp_path / "sample.xlsx"

    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"id": [1]}).to_excel(
            writer,
            sheet_name="First",
            index=False,
        )
        pd.DataFrame({"id": [2]}).to_excel(
            writer,
            sheet_name="Second",
            index=False,
        )

    df = load_data(path, sheet="1")

    assert df["id"].tolist() == [2]


def test_rejects_unsupported_file_type(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("id\n1\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_data(path)
