"""Read-only admin authentication tests: synthetic identities, zero live credentials."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient

from webapp import saas
from webapp.app import app

client = TestClient(app)


def _admin_env(monkeypatch, owner=None):
    owner = owner or str(uuid.uuid4())
    monkeypatch.setenv("DQD_ADMIN_ENABLED", "1")
    monkeypatch.setenv("DQD_ADMIN_USER_ID", owner)
    monkeypatch.setenv("SUPABASE_URL", "https://sample-project.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "fake_public_key")
    monkeypatch.setenv("DQD_SAAS_DATABASE_URL", "postgresql://fake:fake@localhost/fake")
    monkeypatch.setenv("DQD_SAAS_ENABLED", "0")
    monkeypatch.setenv("DQD_SAAS_LAUNCH_APPROVED", "0")
    return owner


def test_admin_is_disabled_without_explicit_verified_uuid(monkeypatch):
    for name in ("DQD_ADMIN_ENABLED", "DQD_ADMIN_USER_ID",
                 "SUPABASE_URL", "SUPABASE_ANON_KEY", "DQD_SAAS_DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)
    assert saas.admin_ready() is False
    assert client.get("/api/saas/admin/config").json()["enabled"] is False
    assert client.get("/api/saas/admin/overview").status_code == 503
    for value in ("", "somebody@example.com", str(uuid.UUID(int=0))):
        monkeypatch.setenv("DQD_ADMIN_USER_ID", value)
        monkeypatch.setenv("DQD_ADMIN_ENABLED", "1")
        monkeypatch.setenv("SUPABASE_URL", "https://sample-project.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "fake")
        monkeypatch.setenv("DQD_SAAS_DATABASE_URL", "postgresql://fake")
        assert saas.admin_ready() is False


def test_admin_enabled_does_not_open_customer_saas(monkeypatch):
    _admin_env(monkeypatch)
    assert saas.admin_ready() is True
    assert saas.ready() is False
    cfg = client.get("/api/saas/admin/config").json()
    assert cfg["enabled"] is True and cfg["mfa_required"] is True
    assert "DQD_ADMIN_USER_ID" not in str(cfg)
    assert client.get("/api/saas/config").json()["enabled"] is False
    assert client.post("/api/saas/analyze",
                       files={"file": ("private.csv", b"a\\n1\\n")}).status_code == 503
    assert client.get("/admin").status_code == 200
    assert "authenticator" in client.get("/admin.js").text.lower()


def test_admin_requires_auth_token_before_any_query(monkeypatch):
    _admin_env(monkeypatch)
    assert client.get("/api/saas/admin/overview").status_code == 401
    assert client.get("/api/saas/admin/overview",
                      headers={"Authorization": "Bearer forged.bad.token"}).status_code == 401


def test_admin_rejects_non_owner_even_if_mfa_authenticated(monkeypatch):
    owner = _admin_env(monkeypatch)
    other = str(uuid.uuid4())
    assert owner != other
    monkeypatch.setattr(saas, "_authenticate_bearer",
                        lambda token, *, require_aal2=False: other)
    with pytest.raises(HTTPException) as rejected:
        saas.admin_id(SimpleNamespace(headers={"authorization": "Bearer valid.fake.token"}))
    assert rejected.value.status_code == 403


def test_admin_mfa_claim_checked_against_verified_signature(monkeypatch):
    owner = _admin_env(monkeypatch)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(saas, "_key_client", lambda url:
                        SimpleNamespace(get_signing_key_from_jwt=lambda token:
                                        SimpleNamespace(key=key.public_key())))
    claims = {
        "sub": owner, "aud": "authenticated", "role": "authenticated",
        "iss": "https://sample-project.supabase.co/auth/v1",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        "aal": "aal1",
    }
    token = jwt.encode(claims, key, algorithm="RS256")
    assert saas._authenticate_bearer(token) == owner  # ordinary user authentication
    with pytest.raises(HTTPException) as rejected:
        saas._authenticate_bearer(token, require_aal2=True)
    assert rejected.value.status_code == 401
    claims["aal"] = "aal2"
    mfa_token = jwt.encode(claims, key, algorithm="RS256")
    assert saas._authenticate_bearer(mfa_token, require_aal2=True) == owner
    with pytest.raises(HTTPException):
        saas._authenticate_bearer(jwt.encode(claims, "fake-secret", algorithm="HS256"),
                                   require_aal2=True)


def test_admin_overview_returns_aggregates_only(monkeypatch):
    owner = _admin_env(monkeypatch)
    monkeypatch.setattr(saas, "_authenticate_bearer",
                        lambda token, *, require_aal2=False: owner)
    class FakeDb:
        index = 0
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def cursor(self):
            return self
        def execute(self, sql):
            assert "SELECT" in sql and "auth.users" not in sql
        def fetchone(self):
            row = [
                {"accounts": 2, "active_pro": 1},
                {"total": 14},
                {"total": 3},
            ][self.index]
            self.index += 1
            return row

    monkeypatch.setattr(saas, "_database", FakeDb)
    response = client.get("/api/saas/admin/overview",
                          headers={"Authorization": "Bearer verified.fake.token"})
    assert response.status_code == 200
    assert response.json()["accounts"] == 2
    assert response.json()["all_time_analyses"] == 14
    assert response.json()["read_only"] is True
    assert "email" not in str(response.json()).lower()
