# Makefile für RotaryArchiv
# Vereinfacht häufige Development-Tasks

.PHONY: help install install-dev lint format test coverage run migrate clean

# Standard-Target
help:
	@echo "RotaryArchiv - Verfügbare Commands:"
	@echo ""
	@echo "  make install          - Installiere Production-Dependencies"
	@echo "  make install-dev      - Installiere Development-Dependencies"
	@echo "  make lint             - Führe Linting aus (Ruff)"
	@echo "  make format           - Formatiere Code (Ruff)"
	@echo "  make test             - Führe Tests aus"
	@echo "  make coverage         - Führe Tests mit Coverage-Report aus"
	@echo "  make run              - Starte FastAPI Server"
	@echo "  make migrate          - Führe Datenbank-Migrationen aus"
	@echo "  make clean            - Entferne temporäre Dateien"
	@echo "  make pre-commit-install - Installiere Pre-commit Hooks"
	@echo ""

# Installation
install:
	pip install --upgrade pip
	pip install -r requirements.txt

install-dev: install
	pip install -r requirements-dev.txt
	@echo "Development-Dependencies installiert. Führe 'make pre-commit-install' aus, um Pre-commit Hooks zu installieren."

# Code Quality
lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

lint-fix:
	ruff check --fix src/ tests/

# Testing
test:
	pytest

test-verbose:
	pytest -v

test-coverage:
	pytest --cov=src.rotary_archiv --cov-report=html --cov-report=term

coverage: test-coverage
	@echo "Coverage-Report erstellt: htmlcov/index.html"

# Server
run:
	uvicorn src.rotary_archiv.main:app --reload --host 0.0.0.0 --port 8000

run-prod:
	uvicorn src.rotary_archiv.main:app --host 0.0.0.0 --port 8000

# Database
migrate:
	alembic upgrade head

migrate-create:
	@echo "Usage: make migrate-create MESSAGE='Beschreibung'"
	@if [ -z "$(MESSAGE)" ]; then echo "Bitte MESSAGE angeben!"; exit 1; fi
	alembic revision --autogenerate -m "$(MESSAGE)"

# Pre-commit
pre-commit-install:
	pre-commit install
	@echo "Pre-commit Hooks installiert!"

pre-commit-run:
	pre-commit run --all-files

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	@echo "Temporäre Dateien entfernt!"

# Windows PowerShell Fallback (wenn Make nicht verfügbar)
# Diese Commands können direkt in PowerShell ausgeführt werden:
#
# Install Dev Dependencies:
#   pip install -r requirements-dev.txt
#
# Linting:
#   ruff check src/ tests/
#
# Formatting:
#   ruff format src/ tests/
#
# Testing:
#   pytest
#
# Run Server:
#   uvicorn src.rotary_archiv.main:app --reload --host 0.0.0.0 --port 8000
#
# Migrations:
#   alembic upgrade head
