"""Configuration. Everything comes from environment variables (twelve-factor), nothing is hard-coded."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    app_version: str
    base_url: str
    database_url: str | None
    redis_url: str | None
    log_level: str
    log_format: str
    max_url_length: int
    code_length: int
    cache_ttl_seconds: int

    @classmethod
    def from_env(cls) -> Settings:
        from api import __version__

        log_format = os.environ.get("LOG_FORMAT", "json").strip().lower()
        if log_format not in {"json", "text"}:
            raise ValueError("LOG_FORMAT must be 'json' or 'text'")
        return cls(
            app_version=os.environ.get("APP_VERSION", __version__).strip() or __version__,
            base_url=os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/"),
            database_url=os.environ.get("DATABASE_URL", "").strip() or None,
            redis_url=os.environ.get("REDIS_URL", "").strip() or None,
            log_level=os.environ.get("LOG_LEVEL", "info").strip().lower(),
            log_format=log_format,
            max_url_length=_int("MAX_URL_LENGTH", 2048),
            code_length=_int("CODE_LENGTH", 6),
            cache_ttl_seconds=_int("CACHE_TTL_SECONDS", 300),
        )
