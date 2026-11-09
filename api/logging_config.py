"""Logging: one JSON object per line by default, so log pipelines (Loki, CloudWatch) can parse it."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

_LEVELS = {"debug": logging.DEBUG, "info": logging.INFO, "warn": logging.WARNING, "warning": logging.WARNING, "error": logging.ERROR}
_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        payload.update({k: v for k, v in record.__dict__.items() if k not in _RESERVED})
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "info", fmt: str = "json") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter() if fmt == "json" else logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(_LEVELS.get(level, logging.INFO))
    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).handlers[:] = []
        logging.getLogger(noisy).propagate = False
