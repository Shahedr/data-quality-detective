"""Vercel root-level FastAPI detection must use the real application."""

import importlib

from fastapi.testclient import TestClient


def test_vercel_entrypoint_reuses_full_application_and_routes(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    entrypoint = importlib.import_module("app")
    from webapp.app import app as original
    assert entrypoint.app is original
    client = TestClient(entrypoint.app)
    assert client.get("/").status_code == 200
    assert client.get("/health").status_code == 200
    config = client.get("/api/config")
    assert config.status_code == 200
    assert config.json()["mode"] == "public_demo"
    assert client.get("/api/demo/analyze").json()["summary"]["rows"] == 12
    response = client.post(
        "/api/analyze", files={"file": ("private.xlsm", b"unsafe-input")}
    )
    assert response.status_code == 403
