"""Behaviour of the public API."""


def shorten(client, url="https://ironhack.com"):
    return client.post("/shorten", json={"url": url})


def test_health_check_returns_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "9.9.9"
    assert body["uptime_seconds"] >= 0


def test_shorten_returns_short_code_and_url(client):
    response = shorten(client)
    assert response.status_code == 200
    body = response.json()
    assert len(body["short_code"]) == 6
    assert body["original_url"] == "https://ironhack.com"
    assert body["short_url"] == f"http://testserver/r/{body['short_code']}"


def test_shorten_stores_the_url(client, store):
    code = shorten(client, "https://github.com").json()["short_code"]
    assert store.get(code) == "https://github.com"


def test_different_urls_get_different_codes(client):
    a = shorten(client, "https://ironhack.com").json()["short_code"]
    b = shorten(client, "https://github.com").json()["short_code"]
    assert a != b


def test_the_same_url_twice_is_allowed(client):
    assert shorten(client).status_code == 200
    assert shorten(client).status_code == 200


def test_redirect_is_a_302_and_not_cacheable(client):
    code = shorten(client).json()["short_code"]
    response = client.get(f"/r/{code}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://ironhack.com"
    assert response.headers["cache-control"] == "no-store"


def test_redirect_unknown_code_returns_404(client):
    assert client.get("/r/doesnotexist").status_code == 404


def test_redirect_rejects_malformed_codes(client):
    assert client.get("/r/bad%20code").status_code == 404


def test_stats_counts_urls_and_reports_storage(client):
    shorten(client, "https://ironhack.com")
    shorten(client, "https://github.com")
    body = client.get("/stats").json()
    assert body["total_urls"] == 2
    assert body["store"] == "memory"
    assert "uptime_seconds" in body


def test_missing_url_field_is_rejected(client):
    assert client.post("/shorten", json={}).status_code == 422


def test_openapi_docs_are_served(client):
    assert client.get("/openapi.json").status_code == 200
