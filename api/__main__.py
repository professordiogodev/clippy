"""Run with: python -m api   (reads APP_HOST and APP_PORT, defaults 0.0.0.0:8000)."""

import os

import uvicorn

DEFAULT_HOST = "0.0.0.0"  # noqa: S104  (a service has to listen on all interfaces inside a container)

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app", host=os.environ.get("APP_HOST", DEFAULT_HOST), port=int(os.environ.get("APP_PORT", "8000"))
    )
