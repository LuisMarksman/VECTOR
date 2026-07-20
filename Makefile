# ===========================================================================
# VECTOR — developer task runner
# ===========================================================================
.DEFAULT_GOAL := help
.PHONY: help setup env server voice vision test lint fmt up down logs clean

PYTHON ?= python3

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

env: ## Create a local .env from the template if missing
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example")

setup: env ## Install Python deps for the server, voice and vision packages
	$(PYTHON) -m pip install -e "server[dev]"
	$(PYTHON) -m pip install -r voice/requirements.txt
	$(PYTHON) -m pip install -r vision/requirements.txt

server: ## Run the AI server with autoreload
	cd server && $(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

voice: ## Run the voice assistant client
	cd voice && $(PYTHON) -m vector_voice

vision: ## Run the vision worker
	cd vision && $(PYTHON) -m vector_vision

test: ## Run the server test suite
	cd server && $(PYTHON) -m pytest -q

lint: ## Static checks (ruff)
	cd server && ruff check .

fmt: ## Auto-format (ruff)
	cd server && ruff format .

up: ## Start the core stack (mqtt + server) with Docker
	docker compose up -d mqtt server

down: ## Stop the Docker stack
	docker compose down

logs: ## Tail server logs
	docker compose logs -f server

clean: ## Remove caches and build artifacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name '.pytest_cache' -prune -exec rm -rf {} +
	rm -rf server/build server/dist
