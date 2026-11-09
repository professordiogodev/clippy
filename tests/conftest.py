import pytest
from fastapi.testclient import TestClient

from api.config import Settings
from api.main import create_app
from api.store import MemoryStore


class FakeCache:
    kind = "fake"

    def __init__(self):
        self.data = {}
        self.healthy = True

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

    def ping(self):
        return self.healthy


@pytest.fixture
def settings():
    return Settings(
        app_version="9.9.9",
        base_url="http://testserver",
        database_url=None,
        redis_url=None,
        log_level="warn",
        log_format="text",
        max_url_length=200,
        code_length=6,
        cache_ttl_seconds=60,
    )


@pytest.fixture
def store():
    return MemoryStore()


@pytest.fixture
def cache():
    return FakeCache()


@pytest.fixture
def client(settings, store, cache):
    with TestClient(create_app(settings, store=store, cache=cache)) as c:
        yield c
