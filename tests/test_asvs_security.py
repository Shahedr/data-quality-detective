"""ASVS browser boundary regression checks for local and hosted modes."""
import re

import pytest
from fastapi.testclient import TestClient

from webapp.app import app


@pytest.mark.parametrize('path', ['/', '/privacy', '/api/config', '/missing', '/app.js'])
def test_security_headers_cover_documents_api_assets_and_errors(path, monkeypatch):
    monkeypatch.setenv('VERCEL', '1')
    response = TestClient(app).get(path)
    policy = response.headers['content-security-policy']
    for directive in ["base-uri 'none'", "object-src 'none'", "frame-ancestors 'none'"]:
        assert directive in policy
    assert response.headers['strict-transport-security'] == 'max-age=31536000'
    assert response.headers['cross-origin-opener-policy'] == 'same-origin'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert response.headers['cache-control'] == 'no-store'
    assert 'set-cookie' not in response.headers


def test_main_page_requires_external_scripts_and_local_has_no_hsts(monkeypatch):
    monkeypatch.delenv('VERCEL', raising=False)
    client = TestClient(app)
    page = client.get('/')
    assert "script-src 'self';" in page.headers['content-security-policy']
    assert 'strict-transport-security' not in page.headers
    assert '<script>' not in page.text
    assert not re.search(r'\son\w+\s*=', page.text, re.I)
    sources = re.findall(r'<script src="([^"]+)"', page.text)
    assert '/app.js' in sources
    for source in sources:
        response = client.get(source)
        assert response.status_code == 200
        assert 'javascript' in response.headers['content-type']


@pytest.mark.parametrize('path', ['/.git/config', '/.env', '/reports', '/docs', '/redoc', '/openapi.json'])
def test_internal_files_and_interactive_docs_are_not_served(path):
    assert TestClient(app).get(path).status_code == 404


def test_trace_is_not_supported():
    assert TestClient(app).request('TRACE', '/').status_code == 405


def test_deployment_identity_allows_smoke_checks_to_wait_for_expected_release(monkeypatch):
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.setenv('VERCEL_GIT_COMMIT_SHA', 'a' * 40)
    assert TestClient(app).get('/api/config').json()['release_sha'] == 'a' * 40
    monkeypatch.delenv('VERCEL_GIT_COMMIT_SHA')
    assert TestClient(app).get('/api/config').json()['release_sha'] == ''
