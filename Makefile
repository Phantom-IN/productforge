# The plugin's interpreter is python3.11 (CLAUDE.md golden rule 9); override with PYTHON=...
PYTHON ?= python3.11
SCRIPTS := skills/productforge/scripts
RUNTIME_PY := $(shell find skills hooks -name '*.py' -not -path '*/__pycache__/*' 2>/dev/null)
MYPY_TARGETS := $(SCRIPTS)/pf.py $(SCRIPTS)/pflib $(wildcard hooks/*.py)

.PHONY: help compile test lint fixtures-check example check clean

help:
	@echo "make compile | test | lint | fixtures-check | example | check | clean"

compile:
	$(PYTHON) -m py_compile $(RUNTIME_PY)

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m mypy $(MYPY_TARGETS)

# The shipped example (= the PHASE_PLAN_READY fixture) must pass every check, lint and trace.
example:
	$(PYTHON) $(SCRIPTS)/pf.py check --workspace examples/tasklet
	$(PYTHON) $(SCRIPTS)/pf.py lint-phases --workspace examples/tasklet
	$(PYTHON) $(SCRIPTS)/pf.py trace --workspace examples/tasklet

# Every synthetic fixture snapshot must validate with zero errors.
fixtures-check:
	$(PYTHON) tests/fixtures/build_tasklet.py --check
	@for ws in tests/fixtures/workspaces/*/*/; do \
		echo "validate $$ws"; \
		$(PYTHON) $(SCRIPTS)/pf.py validate --workspace "$$ws" || exit 1; \
	done

# examples/tasklet joins in Phase 17.
check: compile test lint fixtures-check example

clean:
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache build *.egg-info
