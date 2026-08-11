# SAIE — top-level Makefile (M01).
#
# Every target is intentionally thin: it delegates to the owning
# subproject so the same commands work whether you are at the repo
# root or inside ``web/`` / ``backend/``. CI invokes these targets
# verbatim, so a target that breaks here breaks the pipeline.
#
# Traceability: NFR-006 (single command to verify the project is
# green), NFR-005 (a single ``make up`` proves the stack is wired).

.PHONY: help install lint typecheck test build up down logs \
        backend-install backend-lint backend-typecheck backend-test backend-build \
        web-install web-lint web-test web-build \
        ci

help:
	@echo "SAIE — M01 make targets"
	@echo "  install     Install backend + web deps"
	@echo "  lint        Lint backend (ruff) + web (eslint)"
	@echo "  typecheck   mypy on the backend"
	@echo "  test        Run all unit tests"
	@echo "  build       Production builds (web dist, backend wheel)"
	@echo "  up          docker compose up (detached)"
	@echo "  down        docker compose down"
	@echo "  logs        docker compose logs -f"
	@echo "  ci          What CI runs (lint + typecheck + test)"

# --- Meta ----------------------------------------------------------------

install: backend-install web-install

lint: backend-lint web-lint

typecheck: backend-typecheck

test: backend-test web-test

build: web-build backend-build

ci: lint typecheck test

# --- Backend -------------------------------------------------------------

backend-install:
	cd backend && python -m pip install -q -r requirements.txt

backend-lint:
	cd backend && .venv/Scripts/python.exe -m ruff check app notifications tests || python -m ruff check app notifications tests

backend-typecheck:
	cd backend && .venv/Scripts/python.exe -m mypy app || python -m mypy app

backend-test:
	cd backend && .venv/Scripts/python.exe -m pytest tests/ notifications/tests/ -v

backend-build:
	cd backend && docker build -t saie-api:dev .

# --- Web -----------------------------------------------------------------

web-install:
	cd web && npm install

web-lint:
	cd web && npm run lint && npm run format:check

web-test:
	cd web && npm test

web-build:
	cd web && npm run build

# --- Docker --------------------------------------------------------------

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f
