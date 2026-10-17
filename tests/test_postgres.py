import os

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from dqdetect.cli import main
from dqdetect.database import load_database_table


DATABASE_URL = os.getenv("DQDETECT_TEST_POSTGRES_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="PostgreSQL integration URL not configured",
)


@pytest.fixture()
def postgres_table():
    engine = create_engine(DATABASE_URL)

    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS dqdetect_orders"))

    pd.DataFrame(
        {
            "id": [1, 2],
            "amount": [10.5, 20.0],
        }
    ).to_sql(
        "dqdetect_orders",
        engine,
        index=False,
    )

    engine.dispose()
    return "dqdetect_orders"


def test_load_postgresql_table(postgres_table):
    df = load_database_table(
        DATABASE_URL,
        postgres_table,
        schema="public",
    )

    assert df["id"].tolist() == [1, 2]
    assert df["amount"].tolist() == [10.5, 20.0]


def test_cli_profiles_postgresql_table(tmp_path, postgres_table):
    output_dir = tmp_path / "reports"

    exit_code = main(
        [
            "--database-url",
            DATABASE_URL,
            "--table",
            postgres_table,
            "--db-schema",
            "public",
            "--format",
            "json",
            "--output",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    assert (output_dir / "public_dqdetect_orders_report.json").exists()
