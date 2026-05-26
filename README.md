# Clipstr

A URL shortening service — the project you'll build DevOps infrastructure around throughout the Ironhack DevOps & Cloud Engineering bootcamp.

By the end of the bootcamp, this application will be:

- Containerised with Docker
- Running on Kubernetes (EKS + AKS)
- Deployed via a CI/CD pipeline (GitHub Actions)
- Provisioned with Terraform
- Backed by PostgreSQL and Redis (instead of the current in-memory store)
- Observable with Prometheus, Grafana, and OpenTelemetry

Right now it's intentionally minimal — a working API you can run locally in under a minute.

---

## Quick start

```bash
# 1. Clone and enter the repo
git clone https://github.com/professordiogodev/clipstr.git
cd clipstr

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the API
uvicorn api.main:app --reload --port 8000
```

The API is now running at `http://localhost:8000`.

Open the interactive docs: `http://localhost:8000/docs`

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthz` | Health check — used by load balancers |
| `POST` | `/shorten` | Submit a URL, get a short code |
| `GET` | `/r/{code}` | Redirect to the original URL |
| `GET` | `/stats` | Basic stats (URL count, uptime) |

### Example

```bash
# Shorten a URL
curl -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://ironhack.com"}'

# Response
{
  "short_code": "aB3xYz",
  "short_url": "http://localhost:8000/r/aB3xYz",
  "original_url": "https://ironhack.com"
}

# Follow the redirect
curl -L http://localhost:8000/r/aB3xYz
```

---

## Development

```bash
make install   # install dependencies
make run       # start the server with hot reload
make test      # run the test suite
```

---

## Architecture (current — Week 1)

```
Client → FastAPI (port 8000) → in-memory dict
```

This will evolve over the bootcamp:

```
Client → Nginx → FastAPI → Redis (cache)
                         → PostgreSQL (persistence)
```

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_VERSION` | `0.1.0` | Version string returned by `/healthz` |
| `BASE_URL` | `http://localhost:8000` | Base URL used to build short URLs |
