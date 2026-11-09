"""PostgresStore and RedisCache with fakes, so their logic is tested without any service running."""

import sys
import types

import pytest

from api.cache import RedisCache, build_cache
from api.store import PostgresStore, build_store


class FakeRedisClient:
    def __init__(self):
        self.data, self.fail = {}, False

    def get(self, key):
        if self.fail:
            raise ConnectionError("redis down")
        return self.data.get(key)

    def set(self, key, value, ex=None):
        if self.fail:
            raise ConnectionError("redis down")
        self.data[key] = value

    def ping(self):
        if self.fail:
            raise ConnectionError("redis down")
        return True


@pytest.fixture
def fake_redis(monkeypatch):
    import redis

    client = FakeRedisClient()
    monkeypatch.setattr(redis.Redis, "from_url", classmethod(lambda cls, url, **kw: client))
    return client


def test_redis_cache_get_set_and_ping(fake_redis):
    cache = build_cache("redis://x:6379", 60)
    assert cache.kind == "redis"
    cache.set("abc", "https://a.com")
    assert cache.get("abc") == "https://a.com"
    assert fake_redis.data == {"clippy:abc": "https://a.com"}
    assert cache.ping() is True


def test_a_dead_redis_never_breaks_lookups(fake_redis):
    cache = RedisCache("redis://x:6379")
    fake_redis.fail = True
    assert cache.get("abc") is None          # degrades to a cache miss
    cache.set("abc", "https://a.com")         # does not raise
    assert cache.ping() is False


class FakeCursor:
    def __init__(self, rows=None, rowcount=1):
        self._rows, self.rowcount = rows or [], rowcount

    def fetchone(self):
        return self._rows[0] if self._rows else None


class FakeConn:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=()):
        s = " ".join(sql.split()).lower()
        if s.startswith("create table"):
            return FakeCursor()
        if s.startswith("insert"):
            code, url = params
            if code in self.db.rows:
                return FakeCursor(rowcount=0)
            self.db.rows[code] = url
            return FakeCursor(rowcount=1)
        if s.startswith("select url"):
            return FakeCursor([(self.db.rows[params[0]],)] if params[0] in self.db.rows else [])
        if s.startswith("select count"):
            return FakeCursor([(len(self.db.rows),)])
        if s.startswith("select 1"):
            if self.db.down:
                raise ConnectionError("db down")
            return FakeCursor([(1,)])
        raise AssertionError(sql)


class FakePool:
    rows: dict = {}
    down = False

    def __init__(self, dsn, **kw):
        type(self).rows = {}
        type(self).down = False
        self.closed = False

    def connection(self, timeout=None):
        return FakeConn(type(self))

    def close(self):
        self.closed = True


@pytest.fixture
def fake_pg(monkeypatch):
    mod = types.ModuleType("psycopg_pool")
    mod.ConnectionPool = FakePool
    monkeypatch.setitem(sys.modules, "psycopg_pool", mod)
    return FakePool


def test_postgres_store_roundtrip_and_conflict(fake_pg):
    store = build_store("postgresql://u:p@h/db")
    assert isinstance(store, PostgresStore) and store.kind == "postgres"
    assert store.save("abc", "https://a.com") is True
    assert store.save("abc", "https://b.com") is False
    assert store.get("abc") == "https://a.com" and store.get("zzz") is None
    assert store.count() == 1
    assert store.ping() is True
    store.close()


def test_postgres_ping_is_false_when_the_database_is_down(fake_pg):
    store = PostgresStore("postgresql://u:p@h/db")
    fake_pg.down = True
    assert store.ping() is False
