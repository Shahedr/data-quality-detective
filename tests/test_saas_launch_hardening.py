"""Verify security gate blocks anonymous uploads before multipart parsing.

All credentials in these tests are synthetic. No real auth or Stripe charges.
"""
from fastapi import HTTPException
from fastapi.testclient import TestClient

from webapp import saas
from webapp.app import app


client = TestClient(app)


def test_disabled_beta_rejects_before_multipart(monkeypatch):
    monkeypatch.setattr(saas, "ready", lambda: False)
    response = client.post(
        "/api/saas/analyze",
        data=b"x" * 25000,
        headers={"content-type": "application/octet-stream"},
    )
    assert response.status_code == 503
    assert "not enabled" in response.json()["detail"]


def test_anonymous_multipart_is_rejected_before_file_parse(monkeypatch):
    monkeypatch.setattr(saas, "ready", lambda: True)
    response = client.post(
        "/api/saas/analyze",
        files={"file": ("private.csv", b"customer,secret\nAlice,1234\n")},
    )
    assert response.status_code == 401
    assert "sign in" in response.json()["detail"].lower()


def test_oversize_body_is_rejected_before_token_verification(monkeypatch):
    monkeypatch.setattr(saas, "ready", lambda: True)

    def must_not_verify(token):
        raise AssertionError("Oversized request was not rejected first.")

    monkeypatch.setattr(saas, "_authenticate_bearer", must_not_verify)
    response = client.post(
        "/api/saas/analyze",
        content=b"x",
        headers={
            "authorization": "Bearer fake.valid.looking",
            "content-length": str(10 * 1024 * 1024),
        },
    )
    assert response.status_code == 413


def test_webhook_does_not_accept_unbounded_requests(monkeypatch):
    monkeypatch.setattr(saas, "ready", lambda: True)
    response = client.post(
        "/api/saas/billing/webhook",
        data=b"{}",
        headers={"content-length": str(saas.MAX_WEBHOOK_BYTES + 1)},
    )
    assert response.status_code == 413


def test_invalid_login_cannot_reach_parser_even_with_small_file(monkeypatch):
    monkeypatch.setattr(saas, "ready", lambda: True)

    def deny(token):
        raise HTTPException(401, "Expired token.")

    monkeypatch.setattr(saas, "_authenticate_bearer", deny)
    response = client.post(
        "/api/saas/analyze",
        files={"file": ("private.xlsx", b"PKfake")},
        headers={"Authorization": "Bearer invalid.jwt.payload"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Expired token."


def test_public_product_and_legal_pages_have_security_headers():
    for path in ("/app", "/product", "/privacy", "/terms"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.headers["content-security-policy"].startswith(
            "default-src 'none'"
        )
        assert response.headers["x-frame-options"] == "DENY"
    product = client.get("/product").text
    assert "Not available for purchase yet" in product
    assert "privacy" in product.lower()
    assert "cancel" in product.lower()
    assert "refund" in product.lower()


def test_disabled_workspace_does_not_load_third_party_auth_sdk():
    html = client.get("/app").text
    script = client.get("/saas.js").text
    assert "src=\"https://cdn.jsdelivr.net" not in html
    assert "await loadAuthSdk()" in script
    assert "if(!response.ok||!cfg.enabled)" in script
