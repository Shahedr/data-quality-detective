"""Run all tests against the isolated local PostgreSQL test database, no skips."""
import os
from pathlib import Path
from urllib.parse import quote

import psycopg
import pytest

password = (Path(__file__).parent.parent / "postgres-test-password.txt").read_text()
with psycopg.connect(host="127.0.0.1", port=55432, user="dqdtest", password=password,
                     dbname="postgres", autocommit=True, connect_timeout=5) as connection:
    if not connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", ("dqd_mvp_test",)).fetchone():
        connection.execute("CREATE DATABASE dqd_mvp_test")
os.environ["DQDETECT_TEST_POSTGRES_URL"] = f"postgresql+psycopg://dqdtest:{quote(password)}@127.0.0.1:55432/dqd_mvp_test"


class NoSkippedTests:
    skipped = 0

    def pytest_runtest_logreport(self, report):
        if report.skipped:
            self.skipped += 1


checks = NoSkippedTests()
result = pytest.main(["-q", "--tb=short"], plugins=[checks])
if checks.skipped:
    raise SystemExit("Incomplete verification: tests were skipped.")
raise SystemExit(result)
