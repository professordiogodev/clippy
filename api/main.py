"""Clippy: URL shortening service.

Endpoints
    GET  /healthz     liveness: the process is up (never touches Postgres or Redis)
    GET  /readyz      readiness: Postgres and Redis (when configured) answer
    POST /shorten     create a short link
    GET  /r/{code}    redirect (302) to the original URL
    GET  /stats       counters and the storage in use
    GET  /metrics     Prometheus metrics

Storage is in memory unless DATABASE_URL is set; Redis caches redirects when REDIS_URL is set.
See docs/operations.md for the details operators need.
"""

from __future__ import annotations

import logging
import re
import secrets
import string
import time
import uuid
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel

from api.cache import Cache, build_cache
from api.config import Settings
from api.logging_config import configure_logging
from api.store import Store, build_store

log = logging.getLogger("clippy")

_ALPHABET = string.ascii_letters + string.digits
_CODE_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class ShortenRequest(BaseModel):
    url: str


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str


def validate_url(raw: str, max_length: int) -> str:
    """Return the cleaned URL or raise a 422. Only absolute http(s) URLs are accepted."""
    url = raw.strip()
    problem = None
    if not url:
        problem = "url must not be empty"
    elif len(url) > max_length:
        problem = f"url is longer than {max_length} characters"
    elif any(ch.isspace() or ord(ch) < 32 for ch in url):
        problem = "url must not contain spaces or control characters"
    else:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https"):
            problem = "url must start with http:// or https://"
        elif not parts.hostname:
            problem = "url must include a host name"
    if problem:
        raise HTTPException(status_code=422, detail=problem)
    return url


def generate_code(store: Store, length: int = 6, attempts: int = 10) -> str | None:
    """Unguessable code (secrets, not random). Returns None if every attempt collided."""
    for _ in range(attempts):
        candidate = "".join(secrets.choice(_ALPHABET) for _ in range(length))
        if store.get(candidate) is None:
            return candidate
    return None


def create_app(settings: Settings | None = None, store: Store | None = None, cache: Cache | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    registry = CollectorRegistry()
    http_total = Counter("clippy_http_requests_total", "HTTP requests", ["method", "path", "status"], registry=registry)
    http_seconds = Histogram("clippy_http_request_duration_seconds", "HTTP request duration", ["method", "path"], registry=registry)
    created_total = Counter("clippy_links_created_total", "Links created", registry=registry)
    redirects_total = Counter("clippy_redirects_total", "Redirect lookups by where the answer came from", ["source"], registry=registry)
    stored_gauge = Gauge("clippy_links_stored", "Links currently stored", registry=registry)
    Gauge("clippy_build_info", "Build information", ["version"], registry=registry).labels(version=settings.app_version).set(1)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging(settings.log_level, settings.log_format)
        app.state.store = store or build_store(settings.database_url)
        app.state.cache = cache or build_cache(settings.redis_url, settings.cache_ttl_seconds)
        log.info("starting", extra={"version": settings.app_version, "store": app.state.store.kind, "cache": app.state.cache.kind})
        yield
        app.state.store.close()
        log.info("stopped")

    app = FastAPI(
        title="Clippy",
        description="A URL shortening service for the Ironhack DevOps bootcamp",
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.started = time.time()
    # Created eagerly as well so the app also works without the lifespan (plain TestClient usage).
    app.state.store = store or None
    app.state.cache = cache or None

    def _store() -> Store:
        if app.state.store is None:
            app.state.store = build_store(settings.database_url)
        return app.state.store

    def _cache() -> Cache:
        if app.state.cache is None:
            app.state.cache = build_cache(settings.redis_url, settings.cache_ttl_seconds)
        return app.state.cache

    @app.middleware("http")
    async def observe(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            elapsed = time.perf_counter() - started
            route = request.scope.get("route")
            path = route.path if route else "unmatched"
            http_total.labels(request.method, path, str(status)).inc()
            http_seconds.labels(request.method, path).observe(elapsed)
            if path != "/metrics":
                log.info("request", extra={"request_id": request_id, "method": request.method, "path": request.url.path,
                                           "route": path, "status": status, "duration_ms": round(elapsed * 1000, 2)})

    @app.get("/healthz", tags=["ops"])
    def health_check() -> dict:
        """Liveness. Used by load balancers and probes; it never calls a dependency."""
        return {"status": "ok", "version": settings.app_version, "uptime_seconds": round(time.time() - app.state.started, 2)}

    @app.get("/readyz", tags=["ops"])
    def readiness(response: Response) -> dict:
        """Readiness. 503 when the database or cache that is configured does not answer."""
        checks = {"store": _store().ping(), "cache": _cache().ping()}
        ok = all(checks.values())
        if not ok:
            response.status_code = 503
        return {"status": "ready" if ok else "not_ready", "checks": checks, "store": _store().kind, "cache": _cache().kind}

    @app.post("/shorten", response_model=ShortenResponse, tags=["api"])
    def shorten_url(request: ShortenRequest) -> ShortenResponse:
        """Accept a long URL and return a short code."""
        url = validate_url(request.url, settings.max_url_length)
        store = _store()
        code = None
        for _ in range(10):
            candidate = generate_code(store, settings.code_length)
            if candidate and store.save(candidate, url):
                code = candidate
                break
        if code is None:
            log.error("could not allocate a unique code")
            raise HTTPException(status_code=503, detail="could not allocate a short code, try again")
        created_total.inc()
        return ShortenResponse(short_code=code, short_url=f"{settings.base_url}/r/{code}", original_url=url)

    @app.get("/r/{code}", tags=["api"])
    def redirect_to_url(code: str):
        """Redirect a short code to the original URL (302, so browsers do not cache it forever)."""
        if not _CODE_RE.match(code):
            raise HTTPException(status_code=404, detail="Short code not found")
        cache = _cache()
        url = cache.get(code)
        source = "cache"
        if url is None:
            url = _store().get(code)
            source = "store"
            if url is not None:
                cache.set(code, url)
        if url is None:
            redirects_total.labels("not_found").inc()
            raise HTTPException(status_code=404, detail=f"Short code '{code}' not found")
        redirects_total.labels(source).inc()
        return RedirectResponse(url=url, status_code=302, headers={"Cache-Control": "no-store"})

    @app.get("/stats", tags=["ops"])
    def stats() -> dict:
        """Basic stats: total URLs stored, uptime and the storage in use."""
        return {
            "total_urls": _store().count(),
            "uptime_seconds": round(time.time() - app.state.started, 2),
            "store": _store().kind,
            "cache": _cache().kind,
        }

    @app.get("/metrics", tags=["ops"], include_in_schema=False)
    def metrics() -> Response:
        stored_gauge.set(_store().count())
        return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        log.exception("unhandled error")
        return JSONResponse({"detail": "internal server error"}, status_code=500)

    return app


app = create_app()
