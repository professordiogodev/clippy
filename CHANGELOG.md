# Changelog

All notable changes. Format: [Keep a Changelog](https://keepachangelog.com/), versions follow [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-11-09

### Added
- Optional PostgreSQL storage (`DATABASE_URL`) and Redis redirect cache (`REDIS_URL`), in-memory remains the default.
- `GET /readyz` (readiness) next to `GET /healthz` (liveness).
- `GET /metrics` in Prometheus format.
- Structured JSON logging (`LOG_LEVEL`, `LOG_FORMAT`) and an `X-Request-ID` header on every response.
- Input validation on `POST /shorten`: only absolute http(s) URLs, trimmed, length limited (422 otherwise).
- `.env.example`, `docs/architecture.md`, `docs/operations.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`.
- CI workflow, issue and pull request templates, `CODEOWNERS`, Dependabot, `.editorconfig`, `.dockerignore`, pre-commit config, `pyproject.toml`.
- Unit tests for validation, operations, storage and backends, plus integration tests against real services.

### Changed
- Redirects are now `302` with `Cache-Control: no-store` (were `301`).
- Short codes come from `secrets` instead of `random`.
- Runtime and development dependencies are split: `requirements.txt` and `requirements-dev.txt`.
- The application is created by `create_app()`; `api.main:app` still works for `uvicorn`.
- Project renamed from Clipstr to Clippy.

### Fixed
- `make lint` works on a fresh clone (ruff is a dev dependency).

## [0.1.0]

- First version: in-memory URL shortener with `/healthz`, `/shorten`, `/r/{code}` and `/stats`.
