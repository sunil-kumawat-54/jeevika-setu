# ======================================================================
# Project AVSAR — Makefile  (targets mandated by TECH_STACK.md §7)
# ======================================================================
SHELL := /bin/bash
# Git Bash on Windows rewrites container-absolute paths like /srv/... ; disable that.
export MSYS_NO_PATHCONV := 1
export MSYS2_ARG_CONV_EXCL := *
COMPOSE := docker compose -f infra/docker-compose.yml --env-file .env
CORE := $(COMPOSE) exec -T -w /srv core
PY := python

.DEFAULT_GOAL := help
.PHONY: help env up down logs ps dev test lint fmt ingest seed migrate drill grounding \
	mock-on mock-off purge latency build clean freeze-tag ci-local wait-healthy \
	verify-sarvam

help:  ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

env:  ## Create .env from .env.example if missing
	@test -f .env || (cp .env.example .env && echo "created .env from .env.example")

build: env  ## Build all images
	$(COMPOSE) build

up: env  ## Start db, redis, core, web (add PROFILE=full for nginx/ivr-bridge)
	$(COMPOSE) up -d --build db redis core web
	@$(MAKE) --no-print-directory wait-healthy

wait-healthy:  ## Block until every service reports healthy
	@echo "waiting for services to become healthy..."
	@for i in $$(seq 1 90); do \
		  db=$$(docker inspect -f '{{.State.Health.Status}}' jeevikasetu-db 2>/dev/null || echo missing); \
		  rd=$$(docker inspect -f '{{.State.Health.Status}}' jeevikasetu-redis 2>/dev/null || echo missing); \
		  co=$$(docker inspect -f '{{.State.Health.Status}}' jeevikasetu-core 2>/dev/null || echo missing); \
		  we=$$(docker inspect -f '{{.State.Health.Status}}' jeevikasetu-web 2>/dev/null || echo missing); \
	  if [ "$$db" = healthy ] && [ "$$rd" = healthy ] && [ "$$co" = healthy ] && [ "$$we" = healthy ]; then \
	    echo "db=$$db redis=$$rd core=$$co web=$$we"; \
	    echo "ALL HEALTHY  ->  core http://localhost:8000  web http://localhost:3000"; exit 0; fi; \
	  sleep 2; \
	done; \
	echo "TIMED OUT waiting for health: db=$$db redis=$$rd core=$$co web=$$we"; \
	$(COMPOSE) ps; exit 1

down:  ## Stop the stack (keeps the db volume)
	$(COMPOSE) down

clean:  ## Stop and DELETE the db volume
	$(COMPOSE) down -v

ps:  ## Show container status
	$(COMPOSE) ps

logs:  ## Tail logs (SVC=core to narrow)
	$(COMPOSE) logs -f --tail=120 $(SVC)

dev:  ## Run uvicorn --reload and next dev concurrently on the host
	@bash scripts/dev.sh

migrate:  ## Apply Alembic migrations inside core
	$(CORE) alembic -c services/core/alembic.ini upgrade head

seed:  ## Migrate + load seeds/ into the DB + demo users + vector indexes
	$(CORE) alembic -c services/core/alembic.ini upgrade head
	$(CORE) python scripts/load_demo.py

ingest:  ## Run pipelines 01-07 in order (writes seeds/, idempotent)
	$(CORE) python pipelines/run_all.py

test:  ## pytest + web tests
	$(CORE) python -m pytest -q
	@cd apps/web && npm run test --if-present

lint:  ## ruff check
	$(CORE) ruff check services pipelines scripts

fmt:  ## ruff format
	ruff format services pipelines scripts

drill:  ## Kill-a-service drill: network off / db down / provider key revoked
	bash scripts/kill_service_drill.sh

verify-sarvam:  ## LIVE Sarvam STT+TTS check in hi/mr/te/en (needs SARVAM_API_KEY; makes billable calls)
	$(CORE) python scripts/verify_sarvam.py --langs $${LANGS:-hi,mr,te,en}

grounding:  ## Prove every numeral in LLM output exists in the tool JSON
	$(CORE) python scripts/verify_grounding.py --n 50

latency:  ## Print per-stage p50/p95 from the running core
	$(CORE) python scripts/latency_report.py

purge:  ## Retention policy dry-run (ARCHITECTURE.md §11). DAYS=30 APPLY=--apply to delete
	$(CORE) python scripts/purge_old.py --days $${DAYS:-90} $${APPLY:-}

mock-on:  ## Force VOICE_PROVIDER=mock + LLM_PROVIDER=mock and restart core
	@bash scripts/set_env.sh VOICE_PROVIDER mock
	@bash scripts/set_env.sh LLM_PROVIDER mock
	$(COMPOSE) up -d --force-recreate --no-deps core
	@$(MAKE) --no-print-directory wait-healthy
	@echo "MOCK MODE ON — zero API keys required"

mock-off:  ## Switch to the real providers named in .env
	@bash scripts/set_env.sh VOICE_PROVIDER $${PROVIDER:-sarvam}
	@bash scripts/set_env.sh LLM_PROVIDER $${LLM:-anthropic}
	$(COMPOSE) up -d --force-recreate --no-deps core
	@$(MAKE) --no-print-directory wait-healthy
	@echo "MOCK MODE OFF — provider=$${PROVIDER:-sarvam} llm=$${LLM:-anthropic}"

freeze-tag:  ## Tag the finale release
	git tag -a finale-v1 -m "AVSAR finale freeze" && git tag -l

ci-local:  ## Run everything CI runs
	$(MAKE) lint && $(MAKE) test && $(MAKE) grounding && cd apps/web && npm run build
