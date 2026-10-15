"""Lifecycle stage names.

Phase 01 only needs the names (artifact ownership in ``catalog``); the state machine
built on them arrives in Phase 02.
"""

from __future__ import annotations

UNINITIALIZED = "UNINITIALIZED"
DISCOVERY = "DISCOVERY"
PRODUCT_MODEL = "PRODUCT_MODEL"
SCOPE_DEFINED = "SCOPE_DEFINED"
ARCHITECTURE_LOCKED = "ARCHITECTURE_LOCKED"
PHASE_PLAN_READY = "PHASE_PLAN_READY"
IMPLEMENTATION = "IMPLEMENTATION"

ORDER: tuple[str, ...] = (
    UNINITIALIZED,
    DISCOVERY,
    PRODUCT_MODEL,
    SCOPE_DEFINED,
    ARCHITECTURE_LOCKED,
    PHASE_PLAN_READY,
    IMPLEMENTATION,
)

# Stages that own artifacts (UNINITIALIZED and IMPLEMENTATION own none).
ARTIFACT_STAGES: tuple[str, ...] = ORDER[1:-1]
