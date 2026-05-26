"""Tests for the Clipstr API."""

import pytest
from fastapi.testclient import TestClient

from api.main import app, _store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_store():
    """Reset the in-memory store before each test."""
    _store.clear()
    yield
    _store.clear()


# --- /healthz -----------------------------------------------------------------


def test_health_check_returns_ok():
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "uptime_seconds" in body


# --- /shorten -----------------------------------------------------------------


def test_shorten_returns_short_code():
    response = client.post("/shorten", json={"url": "https://ironhack.com"})
    assert response.status_code == 200
    body = response.json()
    assert "short_code" in body
    assert len(body["short_code"]) == 6
    assert body["original_url"] == "https://ironhack.com"
    assert "/r/" in body["short_url"]


def test_shorten_stores_url():
    response = client.post("/shorten", json={"url": "https://github.com"})
    code = response.json()["short_code"]
    assert code in _store
    assert _store[code] == "https://github.com"


def test_shorten_different_codes_for_different_urls():
    r1 = client.post("/shorten", json={"url": "https://ironhack.com"})
    r2 = client.post("/shorten", json={"url": "https://github.com"})
    assert r1.json()["short_code"] != r2.json()["short_code"]


# --- /r/{code} ----------------------------------------------------------------


def test_redirect_returns_301():
    shorten = client.post("/shorten", json={"url": "https://ironhack.com"})
    code = shorten.json()["short_code"]

    response = client.get(f"/r/{code}", follow_redirects=False)
    assert response.status_code == 301
    assert response.headers["location"] == "https://ironhack.com"


def test_redirect_unknown_code_returns_404():
    response = client.get("/r/doesnotexist")
    assert response.status_code == 404


# --- /stats -------------------------------------------------------------------


def test_stats_returns_total_urls():
    client.post("/shorten", json={"url": "https://ironhack.com"})
    client.post("/shorten", json={"url": "https://github.com"})

    response = client.get("/stats")
    assert response.status_code == 200
    assert response.json()["total_urls"] == 2
