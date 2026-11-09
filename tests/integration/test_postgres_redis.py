"""Run against real services:  DATABASE_URL=... REDIS_URL=... make test-integration"""

import os

import pytest
from fastapi.testclient import TestClient

from api.cache import RedisCache
from api.config import Settings
from api.main import create_app
from api.store import PostgresStore

DATABASE_URL = os.environ.get("DATABASE_URL")
REDIS_URL = os.environ.get("REDIS_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not (DATABASE_URL and REDIS_URL), reason="DATABASE_URL and REDIS_URL are not set"),
]


@pytest.fixture
def real_client():
    settings = Settings.from_env()
    store = PostgresStore(DATABASE_URL)
    cache = RedisCache(REDIS_URL, 60)
    with TestClient(create_app(settings, store=store, cache=cache)) as c:
        yield c


def test_readiness_reports_both_services(real_client):
    body = real_client.get("/readyz").json()
    assert body["status"] == "ready"
    assert body["store"] == "postgres" and body["cache"] == "redis"


def test_links_survive_in_postgres_and_redirect(real_client):
    code = real_client.post("/shorten", json={"url": "https://ironhack.com/integration"}).json()["short_code"]
    first = real_client.get(f"/r/{code}", follow_redirects=False)
    second = real_client.get(f"/r/{code}", follow_redirects=False)  # served from Redis
    assert first.status_code == second.status_code == 302
    assert second.headers["location"] == "https://ironhack.com/integration"


def test_a_second_store_instance_sees_the_same_data(real_client):
    code = real_client.post("/shorten", json={"url": "https://ironhack.com/persist"}).json()["short_code"]
    other = PostgresStore(DATABASE_URL)
    try:
        assert other.get(code) == "https://ironhack.com/persist"
    finally:
        other.close()
