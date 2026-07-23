# Reproducibility entrypoint (§8.5). `make all` from a clean clone, with the
# committed data/raw cache, regenerates every figure and number in the report.
#
# Windows: run under Git Bash (has `make`), or invoke the PY commands directly.
PY := .venv/Scripts/python.exe

.PHONY: help install fetch test verify lint analysis figures report all clean

help:
	@echo "install   - create venv and install pinned deps"
	@echo "fetch     - populate data/raw cache from source (needs .env for --refresh)"
	@echo "test      - run the test suite"
	@echo "verify    - [Phase 1] fail if any published row is unverified"
	@echo "lint      - [Phase 1] fail on orphan numbers / advisory language"
	@echo "analysis  - [Phase 3] regime labels, aggregate, pairs, failures, sensitivity"
	@echo "figures   - [Phase 3] regenerate all light-theme charts"
	@echo "all       - [Phase 4] verify + lint + analysis + figures + report checks"

install:
	python -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt

fetch:
	$(PY) -m src.fetch_market

# Force a re-pull from the DB / yfinance (requires .env). Rewrites the cache.
refresh:
	$(PY) -m src.fetch_market --refresh

test:
	$(PY) -m pytest -q

# --- Verification machinery (Phase 1) ------------------------------------
# verify: fail if any published row is unverified (§3.3, §8.1).
verify:
	$(PY) -m src.verify

# lint: orphan-number lint (§8.2) + advisory-language lint (§8.3/§8.4).
lint:
	$(PY) -m src.lint_fabrication
	$(PY) -m src.lint_language

analysis:
	@echo "analysis.py — Phase 3 (not yet built)"

figures:
	@echo "figures — Phase 3 (not yet built)"

all: test verify lint analysis figures
	@echo "make all — full pipeline wires up at Phase 4"

clean:
	rm -rf __pycache__ src/__pycache__ tests/__pycache__ .pytest_cache
