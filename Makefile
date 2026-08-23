.PHONY: dev dev-api dev-web test test-unit test-schema test-invariant test-golden test-cross-view test-e2e test-all lint typecheck golden-update trace calibration release-check

# ─── Unified Entry Points ──────────────────────────────────────────────

dev:
	@echo "Starting API + Web in parallel..."
	@make -j2 dev-api dev-web

dev-api:
	cd apps/api && uvicorn main:app --reload --port 8000

dev-web:
	cd apps/web && npm run dev

# ─── Test Commands ─────────────────────────────────────────────────────

test: test-all

test-unit:
	cd apps/api && python -m pytest ../../tests/unit -v
	cd apps/web && npm run test -- --run

test-schema:
	cd apps/api && python -m pytest ../../tests/unit/test_schemas.py -v

test-invariant:
	cd apps/api && python -m pytest ../../tests/invariant -v

test-golden:
	cd apps/api && python -m pytest ../../tests/golden -v

test-cross-view:
	cd apps/web && npm run test -- --run tests/cross_view

test-e2e:
	cd apps/web && npx playwright test

test-all: test-unit test-schema test-invariant test-golden test-cross-view
	@echo "All tests passed."

# ─── Quality ───────────────────────────────────────────────────────────

lint:
	cd apps/api && python -m ruff check ../../simulator ../../validation ../../tests
	cd apps/web && npm run lint

typecheck:
	cd apps/api && python -m mypy ../../simulator ../../validation
	cd apps/web && npx tsc --noEmit

# ─── Utilities ─────────────────────────────────────────────────────────

golden-update:
	@echo "WARNING: Golden updates require explicit human review."
	@echo "Usage: make golden-update SCENARIO=<name> PROFILE=<name>"
	@test -n "$(SCENARIO)" || (echo "SCENARIO is required" && exit 1)
	cd apps/api && python -m pytest ../../tests/golden --snapshot-update -v

trace:
	@test -n "$(SCENARIO)" || (echo "SCENARIO is required" && exit 1)
	@test -n "$(PROFILE)" || (echo "PROFILE is required" && exit 1)
	cd apps/api && python -m simulator.scripts.trace_runner --scenario $(SCENARIO) --profile $(PROFILE)

calibration:
	@test -n "$(PROFILE)" || (echo "PROFILE is required" && exit 1)
	@test -n "$(REFERENCE)" || (echo "REFERENCE is required" && exit 1)
	cd apps/api && python -m simulator.scripts.calibration_runner --profile $(PROFILE) --reference $(REFERENCE)

release-check:
	@echo "Running full release gate..."
	@make test-all
	@make lint
	@make typecheck
	@echo "Release check complete."
