.PHONY: help install install-dev run run-prod test test-integration lint format check env clean

PYTHON ?= python3

help:
	@echo "Targets:"
	@echo "  make install           Install runtime dependencies"
	@echo "  make install-dev       Install runtime + test + lint dependencies"
	@echo "  make run               Start the API with hot reload (http://localhost:8000)"
	@echo "  make run-prod          Start the API the way a server runs it (no reload)"
	@echo "  make test              Unit tests with coverage (no database needed)"
	@echo "  make test-integration  Tests against real PostgreSQL and Redis (needs DATABASE_URL and REDIS_URL)"
	@echo "  make lint              ruff check"
	@echo "  make format            ruff format and import sorting"
	@echo "  make check             lint + tests (what CI runs)"
	@echo "  make env               Create .env from .env.example"
	@echo "  make clean             Remove caches"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

run:
	uvicorn api.main:app --reload --port 8000

run-prod:
	uvicorn api.main:app --host 0.0.0.0 --port 8000

test:
	pytest -m "not integration" --cov

test-integration:
	pytest -m integration -v

lint:
	ruff check api tests
	ruff format --check api tests

format:
	ruff check --fix api tests
	ruff format api tests

check: lint test

env:
	@test -f .env && echo ".env already exists" || (cp .env.example .env && echo "created .env")

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
