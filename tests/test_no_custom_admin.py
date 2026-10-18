"""The app intentionally has no duplicate owner/admin console.

Supabase Studio/Authentication remain the owner's administration tools.
End-user SaaS authorization still requires the two independent release gates.
"""
from fastapi.testclient import TestClient
from webapp.app import app

client = TestClient(app)


def test_separate_web_admin_routes_do_not_exist(monkeypatch):
    monkeypatch.setenv("DQD_ADMIN_ENABLED", "1")
    monkeypatch.setenv("DQD_ADMIN_SETUP_ENABLED", "1")
    monkeypatch.setenv("DQD_ADMIN_METRICS_RPC_ENABLED", "1")
    for path in ("/admin", "/admin.js", "/api/saas/admin/config",
                 "/api/saas/admin/overview"):
        r = client.get(path)
        assert r.status_code == 404, (path, r.status_code)


def test_no_admin_flags_open_customer_billing_or_uploads(monkeypatch):
    monkeypatch.setenv("DQD_ADMIN_ENABLED", "1")
    monkeypatch.setenv("DQD_ADMIN_SETUP_ENABLED", "1")
    monkeypatch.setenv("DQD_ADMIN_METRICS_RPC_ENABLED", "1")
    monkeypatch.setenv("DQD_SAAS_ENABLED", "0")
    monkeypatch.setenv("DQD_SAAS_LAUNCH_APPROVED", "0")
    assert client.get("/api/saas/config").json()["enabled"] is False
    assert client.post("/api/saas/analyze",
                       files={"file": ("a.csv", b"a\n1\n")}).status_code == 503
    assert client.post("/api/saas/billing/checkout").status_code == 503
    monkeypatch.setenv("VERCEL", "1")
    assert client.post("/api/analyze",
                       files={"file": ("a.csv", b"a\n1\n")}).status_code == 403
