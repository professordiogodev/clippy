# Operations runbook

What an operator needs to run Clippy. Everything here is true for the code in this repository.

## Run

| What | Value |
|------|-------|
| Start command | `uvicorn api.main:app --host 0.0.0.0 --port 8000` (or `python -m api`) |
| Port | 8000 (HTTP). No TLS: terminate it at Nginx or a load balancer. |
| Working directory | the repository root (the package is `api`) |
| Python | 3.11 to 3.13, dependencies from `requirements.txt` (runtime only) |
| User | any unprivileged user. It needs no root and writes no files. |
| Shutdown | `SIGTERM`. uvicorn finishes in-flight requests and the app closes its database pool. |

Run **one worker per process unless `DATABASE_URL` is set**. With the in-memory store every worker has its own data.

## Health and readiness

| Endpoint | Meaning | Failure means |
|----------|---------|---------------|
| `GET /healthz` | The process runs | Restart it |
| `GET /readyz` | Configured Postgres and Redis answer | Stop sending traffic. Do not restart the API: fix the dependency. |

`/readyz` returns `{"status": "ready" | "not_ready", "checks": {"store": bool, "cache": bool}, "store": "memory|postgres", "cache": "none|redis"}`.

## Metrics (Prometheus, `GET /metrics`)

| Metric | Type | Labels |
|--------|------|--------|
| `clippy_http_requests_total` | counter | `method`, `path` (route template), `status` |
| `clippy_http_request_duration_seconds` | histogram | `method`, `path` |
| `clippy_links_created_total` | counter | |
| `clippy_redirects_total` | counter | `source` = `cache`, `store`, `not_found` |
| `clippy_links_stored` | gauge | |
| `clippy_build_info` | gauge | `version` |

Good starting alerts: 5xx ratio above 1% for 5 minutes; p95 `clippy_http_request_duration_seconds` above 500 ms; `/readyz` failing; a drop of `clippy_redirects_total{source="cache"}` share (Redis problems).

## Logs

JSON, one object per line, on stdout. Every request logs one line:

```json
{"ts":"2026-11-09T10:15:00.123+00:00","level":"info","logger":"clippy","msg":"request","request_id":"9c1f...","method":"GET","path":"/r/aB3xYz","route":"/r/{code}","status":302,"duration_ms":1.8}
```

Startup logs the version, store and cache in use. `LOG_FORMAT=text` is easier to read while developing. Send the request id to support: it ties a customer complaint to one log line (the same id is in the `X-Request-ID` response header).

## Failure modes

| Symptom | Likely cause | What to do |
|---------|--------------|------------|
| `/readyz` returns 503, `cache: false` | Redis is down or unreachable | Redirects still work, only slower. Fix Redis. |
| `/readyz` returns 503, `store: false` | Postgres is down, wrong `DATABASE_URL`, or a firewall | Check the connection string, `psql "$DATABASE_URL"`, security groups. |
| App does not start, `connection refused` | `DATABASE_URL` set but Postgres is not reachable at startup | The app needs the database at boot. Start it first or let the orchestrator retry. |
| Links disappear after a restart | No `DATABASE_URL`: in-memory store | Expected. Set `DATABASE_URL`. |
| The same code returns 404 on some requests | Several instances, in-memory store | Each instance has its own data. Use Postgres. |
| 422 on `/shorten` | URL is empty, too long, has spaces, or is not http(s) | Fix the client. The `detail` field says why. |
| 503 on `/shorten`, "could not allocate a short code" | Ten random codes in a row collided (store nearly full) | Raise `CODE_LENGTH`. |
| Port 8000 already in use | A previous process is still running | `ss -ltnp | grep 8000`, stop it. |

## Dependencies

- PostgreSQL 13+ (uses `INSERT ... ON CONFLICT`). Table `links(code text primary key, url text, created_at timestamptz)`.
- Redis 6+. Keys are `clippy:<code>` with a TTL of `CACHE_TTL_SECONDS`.

## Backup and data

Only PostgreSQL holds data. Back it up with `pg_dump`. Redis holds nothing that cannot be rebuilt.
