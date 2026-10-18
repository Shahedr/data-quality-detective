"""Vercel root-level FastAPI detection must use the real application."""

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient


def test_vercel_entrypoint_reuses_full_application_and_routes(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    path = Path(__file__).resolve().parents[1] / "app.py"
    spec = importlib.util.spec_from_file_location("dqd_vercel_entry", path)
    entrypoint = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entrypoint)
    from webapp.app import app as original
    assert entrypoint.app is original
    client = TestClient(entrypoint.app)
    assert client.get("/").status_code == 200
    assert client.get("/health").status_code == 200
    config = client.get("/api/config")
    assert config.status_code == 200
    assert config.json()["mode"] == "free_web"
    assert config.json()["upload_allowed"] is True
    response = client.post(
        "/api/analyze", files={"file": ("actual.csv", b"x\nhello\n")}
    )
    assert response.status_code == 200, response.text
    assert response.json()["summary"]["rows"] == 1
    assert client.get("/api/saas/config").status_code == 404
