from contextlib import nullcontext

import pandas as pd


def load_database_table(database_url, table, schema=None):
    if not database_url:
        raise ValueError(
            "Database URL is required. Set --database-url or "
            "DQDETECT_DATABASE_URL."
        )

    if not table:
        raise ValueError("Database table name is required")

    try:
        from sqlalchemy import MetaData, Table, create_engine, select
        from sqlalchemy.exc import SQLAlchemyError
    except ImportError as exc:
        raise ImportError(
            "Database profiling requires the optional database dependencies. "
            "Install them with: pip install 'dqdetect[database]'"
        ) from exc

    engine = create_engine(database_url)

    try:
        metadata = MetaData(schema=schema)
        table_object = Table(table, metadata, autoload_with=engine)
        statement = select(table_object)

        connection_context = (
            engine.connect() if hasattr(engine, "connect") else nullcontext(engine)
        )
        with connection_context as connection:
            return pd.read_sql(statement, connection)
    except SQLAlchemyError as exc:
        raise ValueError(f"Could not read database table: {exc}") from exc
    finally:
        engine.dispose()
