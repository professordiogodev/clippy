# Clippy

[![CI](https://github.com/professordiogodev/clippy/actions/workflows/ci.yml/badge.svg)](https://github.com/professordiogodev/clippy/actions/workflows/ci.yml)

A small URL shortening service: the application you build DevOps infrastructure around in the Ironhack DevOps & Cloud Engineering bootcamp.

It is deliberately simple to read and complete enough to operate. It has everything a DevOps engineer expects from a service: health and readiness endpoints, Prometheus metrics, structured logs, configuration from environment variables, optional PostgreSQL and Redis, tests, and a CI pipeline. What it does not have is a Dockerfile, Terraform, Ansible or Kubernetes manifests. Those are your job.

## Quick start

You need Python 3.11, 3.12 or 3.13 (Ubuntu 24.04 ships 3.12).

```bash
git clone https://github.com/professordiogodev/clippy.git
cd clippy
python3 -m venv venv
source venv/bin/activate
make install-dev          # runtime + test + lint tools
make run                  # http://localhost:8000
```

Open the interactive API docs at `http://localhost:8000/docs`.

```bash
curl -s -X POST localhost:8000/shorten -H 'Content-Type: application/json' -d '{"url": "https://ironhack.com"}'
# {"short_code":"aB3xYz","short_url":"http://localhost:8000/r/aB3xYz","original_url":"https://ironhack.com"}

curl -i localhost:8000/r/aB3xYz        # 302 Found, Location: https://ironhack.com
curl -s localhost:8000/healthz
curl -s localhost:8000/readyz
curl -s localhost:8000/metrics | head
```

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/healthz` | **Liveness.** The process is up. Never calls Postgres or Redis. Use for liveness probes and load balancer health checks. |
| `GET` | `/readyz` | **Readiness.** Returns 503 when a configured Postgres or Redis does not answer. Use for readiness probes and for taking an instance out of rotation. |
| `POST` | `/shorten` | Create a short link. Only absolute `http://` and `https://` URLs up to `MAX_URL_LENGTH` are accepted (422 otherwise). |
| `GET` | `/r/{code}` | Redirect with `302`. 404 for unknown codes. |
| `GET` | `/stats` | Number of links, uptime and which storage and cache are in use. |
| `GET` | `/metrics` | Prometheus metrics (request counts and latency, links created, redirects by source, build info). |
| `GET` | `/docs` | Interactive OpenAPI documentation. |

Every response carries an `X-Request-ID` header (your own is echoed back), and the same id is in the log line for the request.

## Configuration

All configuration is environment variables. Copy `.env.example` to `.env` (`make env`) to see them all with comments. `.env` is in `.gitignore`: never commit it.

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_VERSION` | the package version | Reported by `/healthz`, `/metrics` and the logs. Your pipeline should set it to the image tag or commit. |
| `BASE_URL` | `http://localhost:8000` | Public base URL used to build short links. |
| `DATABASE_URL` | empty (in-memory) | `postgresql://USER:PASSWORD@HOST:5432/DATABASE`. The `links` table is created on startup. |
| `REDIS_URL` | empty (no cache) | `redis://HOST:6379`. Redirects are cached. A broken Redis degrades to cache misses, it never breaks redirects. |
| `CACHE_TTL_SECONDS` | `300` | How long a redirect stays cached. |
| `LOG_LEVEL` | `info` | `debug`, `info`, `warn`, `error`. |
| `LOG_FORMAT` | `json` | `json` (one object per line) or `text`. |
| `MAX_URL_LENGTH` | `2048` | Longest accepted URL. |
| `CODE_LENGTH` | `6` | Length of generated short codes. |
| `APP_HOST`, `APP_PORT` | `0.0.0.0`, `8000` | Only used by `python -m api`. With `uvicorn` use `--host` and `--port`. |

## Storage: important for operators

- **Without `DATABASE_URL` the data lives in the memory of one process.** It disappears on restart, and with `--workers 2` or two replicas every instance has its own, different data. That is on purpose in the first weeks, so you can see why a shared database is needed.
- With `DATABASE_URL` all instances share one PostgreSQL. With `REDIS_URL` they also share a cache.
- Moving between the two needs no code change, only environment variables.

## Development

```bash
make install-dev          # install everything
make run                  # hot reload
make test                 # unit tests + coverage (no services needed)
make test-integration     # needs DATABASE_URL and REDIS_URL
make lint                 # ruff
make format               # fix style
make check                # lint + tests: what CI runs
make help                 # all targets
```

Run it like a server does (no reload, all interfaces):

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
# or: python -m api
```

### Repository layout

```text
api/
  main.py             routes, validation, metrics, middleware
  config.py           settings from environment variables
  store.py            in-memory and PostgreSQL storage
  cache.py            Redis cache
  logging_config.py   JSON logging
tests/                unit tests (no services) and tests/integration (real Postgres and Redis)
docs/                 architecture and operations runbook
.env.example          every setting, documented
.github/              CI workflow, issue and pull request templates, CODEOWNERS
```

## Documentation

- [Architecture](docs/architecture.md): components and how requests flow
- [Operations](docs/operations.md): ports, health, metrics, logs, failure modes, what to monitor
- [Contributing](CONTRIBUTING.md): branches, commits, pull requests
- [Changelog](CHANGELOG.md) and [Security policy](SECURITY.md)

## How Clippy is used in the bootcamp

| Stage | What you do with it |
|-------|---------------------|
| Weeks 1-2 | Run it on a Linux server, manage it with systemd, put Nginx in front, deploy it on AWS |
| Week 3 (Project 1) | Provision and operate it with Terraform and shell scripts: VMs, PostgreSQL, Redis, a jump host |
| Weeks 4-5 | Containerise it, configure servers with Ansible, build CI/CD pipelines |
| Week 6 (Project 2) | Ship it through a secure pipeline: tests, scans, approvals, rollback |
| Weeks 7-8 | Run it on Kubernetes and observe it with Prometheus, Grafana and logs |

## License

MIT, see [LICENSE](LICENSE).
