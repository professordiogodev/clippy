.PHONY: install run test lint help

help:
	@echo "Available targets:"
	@echo "  make install   Install Python dependencies"
	@echo "  make run       Start the API server (http://localhost:8000)"
	@echo "  make test      Run the test suite"
	@echo "  make lint      Check code style (requires ruff)"

install:
	pip install -r requirements.txt

run:
	uvicorn api.main:app --reload --port 8000

test:
	pytest tests/ -v

lint:
	ruff check api/ tests/
