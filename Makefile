# The plugin's interpreter is python3.11 (CLAUDE.md golden rule 9); override with PYTHON=...
PYTHON ?= python3.11
SCRIPTS := skills/productforge/scripts
RUNTIME_PY := $(shell find skills hooks -name '*.py' -not -path '*/__pycache__/*' 2>/dev/null)
MYPY_TARGETS := $(SCRIPTS)/pf.py $(SCRIPTS)/pflib $(wildcard hooks/*.py)

.PHONY: help compile test lint check clean

help:
	@echo "make compile | test | lint | check | clean"

compile:
	$(PYTHON) -m py_compile $(RUNTIME_PY)

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m mypy $(MYPY_TARGETS)

# Example/fixture validation is added to `check` in Phase 03.
check: compile test lint

clean:
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache build *.egg-info
