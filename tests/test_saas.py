"""Fail-closed SaaS regression tests; no real customer credentials required."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import uuid

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from webapp.app import app
from webapp import saas

client = TestClient(app)


def test_beta_closed_without_explicit_lawful_launch_approval(monkeypatch):
    for key in (
        "DQD_SAAS_ENABLED", "DQD_SAAS_LAUNCH_APPROVED",
        "SUPABASE_URL", "SUPABASE_ANON_KEY",
        "DQD_SAAS_DATABASE_URL", "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET", "STRIPE_PRO_PRICE_ID",
        "DQD_SITE_URL", "DQD_LEGAL_ENTITY", "DQD_PRIVACY_EMAIL",
    ):
        monkeypatch.delenv(key, raising=False)
    assert client.get("/api/saas/config").json()["enabled"] is False
    assert client.get("/app").status_code == 200
    assert client.get("/privacy").status_code == 200
    assert client.get("/terms").status_code == 200
    for endpoint in ("/api/saas/account", "/api/saas/rows"):
        assert client.get(endpoint).status_code == 503
    assert client.post(
        "/api/saas/analyze", files={"file": ("private.csv", b"a\n1\n")}
    ).status_code == 503
    assert client.post(
        "/api/saas/billing/webhook", data=b"{}"
    ).status_code == 503


def env(monkeypatch, approved=True):
    fields = {
        "DQD_SAAS_ENABLED": "1",
        "DQD_SAAS_LAUNCH_APPROVED": "1" if approved else "0",
        "SUPABASE_URL": "https://sample-project.supabase.co",
        "SUPABASE_ANON_KEY": "public-anon-key",
        "DQD_SAAS_DATABASE_URL": "postgresql://irrelevant:secret@localhost:5432/dqd",
        "STRIPE_SECRET_KEY": "sk_test_not_real",
        "STRIPE_WEBHOOK_SECRET": "whsec_not_real",
        "STRIPE_PRO_PRICE_ID": "price_test_not_real",
        "DQD_SITE_URL": "https://example.test",
        "DQD_LEGAL_ENTITY": "Example Operator LLC",
        "DQD_PRIVACY_EMAIL": "privacy@example.test",
    }
    for key, value in fields.items():
        monkeypatch.setenv(key, value)


def test_beta_needs_human_approval_even_with_credentials(monkeypatch):
    env(monkeypatch, approved=False)
    assert saas.ready() is False
    assert client.post(
        "/api/saas/analyze", files={"file": ("private.csv", b"x\n1\n")}
    ).status_code == 503


def test_beta_blocks_unauthorized_files_and_billing(monkeypatch):
    env(monkeypatch)
    assert client.get("/api/saas/config").json()["enabled"] is True
    assert client.get("/api/saas/account").status_code == 401
    assert client.post("/api/saas/billing/checkout").status_code == 401
    assert client.post("/api/saas/billing/portal").status_code == 401
    assert client.delete("/api/saas/account").status_code == 401
    response = client.post(
        "/api/saas/analyze",
        files={"file": ("private.xlsm", b"PK_not_valid")},
        headers={"Authorization": "Bearer forged.token.here"},
    )
    assert response.status_code == 401


def test_beta_rejects_webhook_without_valid_signature(monkeypatch):
    env(monkeypatch)
    response = client.post(
        "/api/saas/billing/webhook",
        data=b'{"id":"evt_fake"}',
        headers={"Stripe-Signature": "t=12345,v1=anything"},
    )
    assert response.status_code == 400


def test_beta_limit_and_file_type_guards(monkeypatch):
    env(monkeypatch)
    monkeypatch.setattr(saas, "account_id", lambda: "fake")
    import asyncio
    from fastapi import UploadFile
    from io import BytesIO

    async def load(name, data):
        return await saas.read_upload(UploadFile(filename=name, file=BytesIO(data)))

    from fastapi import HTTPException
    import pytest
    with pytest.raises(HTTPException) as big:
        asyncio.run(load("big.csv", b"x" * (saas.MAX_UPLOAD_BYTES + 1)))
    assert big.value.status_code == 413
    with pytest.raises(HTTPException) as disallowed:
        asyncio.run(load("macro.vbs", b"evil"))
    assert disallowed.value.status_code == 415
    assert asyncio.run(load("small.csv", b"a,b\n1,2\n"))[1].startswith(b"a,b")


def test_asymmetric_jwt_verification_checks_issuer_audience_role_and_exp(monkeypatch):
    env(monkeypatch)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(saas, "_key_client", lambda url:
                        SimpleNamespace(get_signing_key_from_jwt=lambda token:
                                        SimpleNamespace(key=key.public_key())))
    subject = str(uuid.uuid4())
    claims = {
        "sub": subject,
        "aud": "authenticated",
        "iss": "https://sample-project.supabase.co/auth/v1",
        "role": "authenticated",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=20),
    }
    token = jwt.encode(claims, key, algorithm="RS256")
    assert saas._authenticate_bearer(token) == subject
    from fastapi import HTTPException
    import pytest

    for updates in (
        {"aud": "anon"},
        {"iss": "https://other-project.supabase.co/auth/v1"},
        {"role": "anon"},
        {"exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
    ):
        altered = claims.copy()
        altered.update(updates)
        with pytest.raises(HTTPException) as denied:
            saas._authenticate_bearer(jwt.encode(altered, key, algorithm="RS256"))
        assert denied.value.status_code == 401

    with pytest.raises(HTTPException):
        saas._authenticate_bearer(jwt.encode(claims, "attacker", algorithm="HS256"))


def test_public_vercel_demo_still_denies_unauthenticated_upload(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    assert client.post(
        "/api/analyze", files={"file": ("private.xlsm", b"PKnotallowed")}
    ).status_code == 403
