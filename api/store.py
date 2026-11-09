"""Link storage. In memory by default, PostgreSQL when DATABASE_URL is set.

The in-memory store is per process: with several workers or replicas each one has its own data.
That is intentional for the early weeks of the bootcamp and the reason a shared database is added later.
"""

from __future__ import annotations

import threading
from typing import Protocol


class Store(Protocol):
    kind: str

    def save(self, code: str, url: str) -> bool:
        """Store a link. Return False if the code already exists."""

    def get(self, code: str) -> str | None: ...

    def count(self) -> int: ...

    def ping(self) -> bool: ...

    def close(self) -> None: ...


class MemoryStore:
    kind = "memory"

    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self._lock = threading.Lock()

    def save(self, code: str, url: str) -> bool:
        with self._lock:
            if code in self._data:
                return False
            self._data[code] = url
            return True

    def get(self, code: str) -> str | None:
        return self._data.get(code)

    def count(self) -> int:
        return len(self._data)

    def ping(self) -> bool:
        return True

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def close(self) -> None:
        return None


class PostgresStore:
    kind = "postgres"

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS links (
        code       text PRIMARY KEY,
        url        text NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now()
    )
    """

    def __init__(self, dsn: str) -> None:
        from psycopg_pool import ConnectionPool

        self._pool = ConnectionPool(dsn, min_size=1, max_size=5, open=True, timeout=5)
        with self._pool.connection() as conn:
            conn.execute(self.SCHEMA)

    def save(self, code: str, url: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "INSERT INTO links (code, url) VALUES (%s, %s) ON CONFLICT (code) DO NOTHING", (code, url)
            )
            return cur.rowcount == 1

    def get(self, code: str) -> str | None:
        with self._pool.connection() as conn:
            row = conn.execute("SELECT url FROM links WHERE code = %s", (code,)).fetchone()
            return row[0] if row else None

    def count(self) -> int:
        with self._pool.connection() as conn:
            return conn.execute("SELECT count(*) FROM links").fetchone()[0]

    def ping(self) -> bool:
        try:
            with self._pool.connection(timeout=2) as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    def close(self) -> None:
        self._pool.close()


def build_store(database_url: str | None) -> Store:
    return PostgresStore(database_url) if database_url else MemoryStore()
