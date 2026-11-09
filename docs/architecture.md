# Architecture

## Components

```text
Client
  |
  v
Clippy API  (FastAPI + uvicorn, port 8000)
  |-- PostgreSQL  (optional, DATABASE_URL)  source of truth for links
  `-- Redis       (optional, REDIS_URL)     read-through cache for redirects
```

Without `DATABASE_URL` and `REDIS_URL` the API runs alone with an in-memory store. This is the default and the way the first weeks of the bootcamp run it.

## Request flows

**Create a link** `POST /shorten`

1. Validate the URL (absolute http or https, length, no whitespace).
2. Generate a random 6-character code with `secrets` (unguessable, not sequential).
3. Insert into the store. If the code already exists, try another one (up to 10 attempts, then 503).
4. Return the code and the short URL.

**Follow a link** `GET /r/{code}`

1. Look in Redis. If found, redirect (source `cache`).
2. Otherwise look in the store. If found, put it in Redis and redirect (source `store`).
3. If it exists nowhere, return 404 (source `not_found`).

The redirect is a `302` with `Cache-Control: no-store`, so browsers do not keep a permanent copy.

## Design decisions

| Decision | Why |
|----------|-----|
| Configuration only from environment variables | Twelve-factor: the same image or artefact runs in every environment. |
| Liveness (`/healthz`) does not call dependencies | A database outage must not make the orchestrator restart healthy API processes. |
| Readiness (`/readyz`) does call them | A broken instance is taken out of rotation without being killed. |
| A dead Redis degrades to cache misses | The cache is an optimisation, never a requirement. |
| `302` instead of `301` | Permanent redirects are cached by browsers, which would break future analytics and link expiry. |
| Metric `path` label is the route template | `/r/{code}` instead of every code, so cardinality stays bounded. |
| JSON logs on stdout | The platform (systemd, Docker, Kubernetes) collects stdout. The app does not manage log files. |
| Schema created at startup | Keeps the project small. A real system would use migrations (Alembic is a good exercise). |
