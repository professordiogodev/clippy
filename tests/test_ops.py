"""What operators rely on: readiness, metrics, request ids, configuration."""

from fastapi.testclient import TestClient

from api.config import Settings
from api.main import create_app
from api.store import MemoryStore


def test_readyz_is_ready_with_healthy_dependencies(client):
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_readyz_is_503_when_the_cache_is_down(client, cache):
    cache.healthy = False
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["checks"]["cache"] is False


def test_healthz_stays_up_when_dependencies_are_down(client, cache):
    cache.healthy = False
    assert client.get("/healthz").status_code == 200


def test_metrics_expose_prometheus_text(client):
    client.post("/shorten", json={"url": "https://ironhack.com"})
    text = client.get("/metrics").text
    assert "clippy_links_created_total 1.0" in text
    assert 'clippy_http_requests_total{method="POST",path="/shorten",status="200"} 1.0' in text
    assert "clippy_http_request_duration_seconds_bucket" in text
    assert 'clippy_build_info{version="9.9.9"} 1.0' in text
    assert "clippy_links_stored 1.0" in text


def test_metrics_count_redirect_sources(client):
    code = client.post("/shorten", json={"url": "https://ironhack.com"}).json()["short_code"]
    client.get(f"/r/{code}", follow_redirects=False)   # store, then cached
    client.get(f"/r/{code}", follow_redirects=False)   # cache
    client.get("/r/nope123", follow_redirects=False)
    text = client.get("/metrics").text
    assert 'clippy_redirects_total{source="store"} 1.0' in text
    assert 'clippy_redirects_total{source="cache"} 1.0' in text
    assert 'clippy_redirects_total{source="not_found"} 1.0' in text


def test_a_request_id_is_generated_and_echoed(client):
    assert len(client.get("/healthz").headers["x-request-id"]) >= 16
    assert client.get("/healthz", headers={"X-Request-ID": "abc-123"}).headers["x-request-id"] == "abc-123"


def test_unmatched_paths_do_not_explode_metric_labels(client):
    client.get("/this/does/not/exist")
    assert 'path="unmatched"' in client.get("/metrics").text


def test_settings_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    monkeypatch.setenv("BASE_URL", "https://s.example.com/")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("MAX_URL_LENGTH", "50")
    s = Settings.from_env()
    assert (s.app_version, s.base_url, s.log_level, s.max_url_length) == ("1.2.3", "https://s.example.com", "debug", 50)
    assert s.database_url is None and s.redis_url is None


def test_defaults_when_nothing_is_set(monkeypatch):
    for name in ("APP_VERSION", "BASE_URL", "DATABASE_URL", "REDIS_URL", "LOG_LEVEL", "LOG_FORMAT"):
        monkeypatch.delenv(name, raising=False)
    s = Settings.from_env()
    assert s.base_url == "http://localhost:8000" and s.log_format == "json" and s.max_url_length == 2048


def test_bad_numbers_fail_fast(monkeypatch):
    monkeypatch.setenv("CODE_LENGTH", "six")
    try:
        Settings.from_env()
    except ValueError as exc:
        assert "CODE_LENGTH" in str(exc)
    else:
        raise AssertionError("expected a ValueError")


def test_base_url_is_used_in_short_urls(settings, store, cache):
    from dataclasses import replace

    app = create_app(replace(settings, base_url="https://s.example.com"), store=store, cache=cache)
    with TestClient(app) as c:
        assert c.post("/shorten", json={"url": "https://ironhack.com"}).json()["short_url"].startswith("https://s.example.com/r/")


def test_unhandled_errors_return_a_clean_500(settings, cache):
    class BrokenStore(MemoryStore):
        def count(self):
            raise RuntimeError("boom")

    app = create_app(settings, store=BrokenStore(), cache=cache)
    with TestClient(app, raise_server_exceptions=False) as c:
        response = c.get("/stats")
    assert response.status_code == 500
    assert response.json() == {"detail": "internal server error"}
