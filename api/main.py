"""
Clipstr — URL shortening service.

Week 1 starting point: in-memory store, no persistence.
Students progressively add: Docker, PostgreSQL, Redis, CI/CD, Kubernetes, Terraform.
"""

import os
import random
import string
import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

app = FastAPI(
    title="Clipstr",
    description="A URL shortening service — Ironhack DevOps bootcamp project",
    version=os.environ.get("APP_VERSION", "0.1.0"),
)

_start_time = time.time()

# In-memory store: {short_code: original_url}
# Replaced with Redis + PostgreSQL in Week 3.
_store: dict[str, str] = {}


# --- Models -------------------------------------------------------------------


class ShortenRequest(BaseModel):
    url: str


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str


# --- Routes -------------------------------------------------------------------


@app.get("/healthz", tags=["ops"])
def health_check() -> dict:
    """Health check endpoint used by load balancers and CI pipelines."""
    return {
        "status": "ok",
        "version": os.environ.get("APP_VERSION", "0.1.0"),
        "uptime_seconds": round(time.time() - _start_time, 2),
    }


@app.post("/shorten", response_model=ShortenResponse, tags=["api"])
def shorten_url(request: ShortenRequest) -> ShortenResponse:
    """Accept a long URL and return a short code."""
    code = _generate_code()
    _store[code] = request.url
    base_url = os.environ.get("BASE_URL", "http://localhost:8000")
    return ShortenResponse(
        short_code=code,
        short_url=f"{base_url}/r/{code}",
        original_url=request.url,
    )


@app.get("/r/{code}", tags=["api"])
def redirect_to_url(code: str):
    """Redirect a short code to the original URL."""
    if code not in _store:
        raise HTTPException(status_code=404, detail=f"Short code '{code}' not found")
    return RedirectResponse(url=_store[code], status_code=301)


@app.get("/stats", tags=["ops"])
def stats() -> dict:
    """Basic stats — total URLs stored, uptime."""
    return {
        "total_urls": len(_store),
        "uptime_seconds": round(time.time() - _start_time, 2),
    }


# --- Helpers ------------------------------------------------------------------


def _generate_code(length: int = 6) -> str:
    """Generate a random alphanumeric short code, guaranteed unique in the store."""
    chars = string.ascii_letters + string.digits
    for _ in range(10):  # retry up to 10 times on collision
        code = "".join(random.choices(chars, k=length))
        if code not in _store:
            return code
    raise RuntimeError("Failed to generate a unique short code after 10 attempts")
