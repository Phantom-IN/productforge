from __future__ import annotations

import re
from pathlib import Path

import pytest

from pflib import catalog, ids, stages

RUNTIME = Path(__file__).resolve().parents[2] / "skills" / "productforge" / "scripts" / "pflib"


def test_every_prefix_lives_in_exactly_one_artifact() -> None:
    for prefix in ids.PREFIXES:
        holders = catalog.specs_for_prefix(prefix)
        assert len(holders) == 1, (prefix, [h.path for h in holders])


def test_every_schema_prefix_is_known_and_unique() -> None:
    seen = [s.prefix for a in catalog.CATALOG for s in a.schemas]
    assert sorted(seen) == sorted(ids.PREFIXES)


def test_schema_field_lists_are_consistent() -> None:
    for spec in catalog.CATALOG:
        assert spec.owner_stage in stages.ARTIFACT_STAGES
        if spec.kind == catalog.KIND_DOCUMENT:
            assert spec.schemas == ()
        for s in spec.schemas:
            fields = set(s.fields)
            assert set(s.ref_fields) <= fields, (s.prefix, set(s.ref_fields) - fields)
            assert set(s.union_fields) <= set(s.ref_fields), s.prefix
            assert set(s.allow_empty) <= fields, s.prefix
            assert {d for d in s.dedupe if d != catalog.TITLE} <= fields, s.prefix
            assert (s.section is None) == (spec.kind == catalog.KIND_RECORD_FILE), s.prefix
            assert (s.owner_stage or spec.owner_stage) in stages.ARTIFACT_STAGES


# every artifact a workspace holds
PLAN_ARTIFACTS = [
    "research/sources.md",
    "research/product-overview.md",
    "research/product-surfaces.md",
    "research/DISCOVERY_LEDGER.md",
    "research/UNKNOWNS.md",
    "research/FEATURE_MATRIX.md",
    "research/workflows/W-001-x.md",
    "spec/DOMAIN_MODEL.md",
    "spec/PERMISSIONS_MATRIX.md",
    "spec/INTEGRATIONS.md",
    "research/architecture-inference.md",
    "research/COMPETITORS.md",
    "spec/PRODUCT_SPEC.md",
    "spec/PARITY_MATRIX.md",
    "spec/ARCHITECTURE.md",
    "spec/decisions/ADR-004-realtime.md",
    "README.md",
    "IMPLEMENTATION_PLAN.md",
    "CLAUDE.md",
    "DEVELOPMENT.md",
    "STARTUP_PROMPT.md",
    "ORCHESTRATOR_PROMPT.md",
    "plans/README.md",
    "plans/phase-00-foundation.md",
    "spec/TRACEABILITY.md",
]


@pytest.mark.parametrize("rel", PLAN_ARTIFACTS)
def test_plan_artifacts_resolve(rel: str) -> None:
    assert catalog.spec_for_path(rel) is not None, rel


def test_lookup_rules() -> None:
    assert catalog.spec_for_path("./research/sources.md").path == "research/sources.md"
    assert catalog.spec_for_path("research/workflows/nested/W-001.md") is None
    assert catalog.spec_for_path("research/workflows/create-task.md") is None
    staged = catalog.spec_for_staged_path("research/workflows/create-task.md")
    assert staged is not None and staged.schema("W") is not None
    assert catalog.spec_for_path("src/app.py") is None


def test_owner_overrides() -> None:
    unknowns = catalog.spec_for_path("research/UNKNOWNS.md")
    assert unknowns is not None
    assert unknowns.owner_of("U") == stages.DISCOVERY
    assert unknowns.owner_of("UD") == stages.SCOPE_DEFINED
    owned = {s.prefix for _, s in catalog.schemas_for_stage(stages.SCOPE_DEFINED)}
    assert owned == {"UD", "SC", "R"}
    assert {s.path for s in catalog.specs_for_stage(stages.PHASE_PLAN_READY)} >= {"CLAUDE.md"}


def test_record_file_path_slug() -> None:
    spec = catalog.spec_for_path("research/workflows/W-001-x.md")
    assert spec is not None
    assert catalog.record_file_path(spec, "W-007", "Create task / assign!") == (
        "research/workflows/W-007-create-task-assign.md"
    )


def test_artifact_paths_are_only_in_catalog() -> None:
    """Golden rule 8: no runtime module other than catalog.py hardcodes artifact paths."""
    pattern = re.compile(r"""["'](?:research|spec|plans)/""")
    offenders = [
        p.name
        for p in RUNTIME.rglob("*.py")
        if p.name != "catalog.py" and pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == []
