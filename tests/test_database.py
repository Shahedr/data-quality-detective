import pandas as pd
from sqlalchemy import create_engine

from dqdetect.database import load_database_table


def test_load_database_table_with_sqlite(tmp_path):
    database_path = tmp_path / "sample.db"
    database_url = f"sqlite:///{database_path}"

    engine = create_engine(database_url)
    pd.DataFrame({"id": [1, 2], "value": ["a", "b"]}).to_sql(
        "orders",
        engine,
        index=False,
    )
    engine.dispose()

    df = load_database_table(database_url, "orders")

    assert df["id"].tolist() == [1, 2]
    assert df["value"].tolist() == ["a", "b"]
