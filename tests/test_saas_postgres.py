"""Exercise SaaS quota transactions against disposable GitHub CI PostgreSQL.

Never runs against a production or real user's database.
"""
from concurrent.futures import ThreadPoolExecutor
import os
import uuid

import psycopg
import pytest
from fastapi import HTTPException
from psycopg.rows import dict_row

from webapp import saas

URL = os.getenv("DQDETECT_TEST_POSTGRES_URL", "").replace(
    "postgresql+psycopg://", "postgresql://", 1
)


@pytest.mark.skipif(not URL, reason="Dedicated disposable GitHub CI Postgres only")
def test_postgres_real_quota_atomicity_and_plan_transitions(monkeypatch):
    if os.getenv("CI") != "true":
        pytest.skip("Refuse real-db tests outside disposable GitHub CI Postgres")
    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    schema = (root / "saas" / "schema.sql").read_text(encoding="utf-8")
    # Vanilla PostgreSQL in GitHub CI has no Supabase-created anon and
    # authenticated roles. Keep the RLS DDL, skip only Supabase role revokes.
    schema = "\n".join(line for line in schema.splitlines()
                       if not line.startswith("REVOKE ALL ON "))
    with psycopg.connect(URL) as conn:
        with conn.cursor() as cur:
            cur.execute(schema)
    monkeypatch.setattr(
        saas, "_database",
        lambda: psycopg.connect(URL, row_factory=dict_row, connect_timeout=5),
    )
    subject = str(uuid.uuid4())

    def attempt(_):
        try:
            saas.meter(subject, "analysis")
            return True
        except HTTPException as exc:
            assert exc.status_code == 429
            return False

    # Concurrent requests must serialize on the individual account lock.
    with ThreadPoolExecutor(max_workers=12) as executor:
        outcomes = list(executor.map(attempt, range(20)))
    assert outcomes.count(True) == saas.FREE_MONTHLY_ANALYSES
    assert outcomes.count(False) == 20 - saas.FREE_MONTHLY_ANALYSES

    with psycopg.connect(URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT analyses FROM saas_monthly_usage WHERE user_id=%s",
                (subject,),
            )
            assert cur.fetchone()["analyses"] == saas.FREE_MONTHLY_ANALYSES
            cur.execute(
                "UPDATE saas_accounts SET subscription_status='active' "
                "WHERE user_id=%s", (subject,)
            )

    # Stripe-driven Pro entitlement permits additional analyses.
    saas.meter(subject, "analysis")
    with psycopg.connect(URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT analyses FROM saas_monthly_usage WHERE user_id=%s",
                (subject,),
            )
            assert cur.fetchone()["analyses"] == saas.FREE_MONTHLY_ANALYSES + 1
            cur.execute(
                "UPDATE saas_accounts SET subscription_status='canceled' "
                "WHERE user_id=%s", (subject,)
            )
    # Cancellation immediately falls back to exhausted free limit.
    with pytest.raises(HTTPException) as exc:
        saas.meter(subject, "analysis")
    assert exc.value.status_code == 429
