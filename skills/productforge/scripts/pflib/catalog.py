"""Artifact catalog (IMPLEMENTATION_PLAN.md §5.1) — the ONLY place artifact paths live.

Each ``ArtifactSpec`` maps a workspace-relative path (or glob) to its owning stage, its
kind, and the schemas of the records it holds. Validators, gates, locks, merge and the
stage guard all read this table; no other module may hardcode an artifact path.

Kinds:
- ``records``      — a file holding records (possibly in several ``##`` sections) + prose.
- ``record-file``  — one record per file (workflows, ADRs); the file body carries extra prose.
- ``document``     — sectioned prose without records (merged section by section).
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field

from pflib import stages
from pflib.errors import UsageError

KIND_RECORDS = "records"
KIND_RECORD_FILE = "record-file"
KIND_DOCUMENT = "document"

CONFIDENCE_SUPPORT_FIELDS = ("Derived from", "Related unknown")
TITLE = "@title"  # dedupe on the record heading title instead of a field

DEDUPE_NORMALISED = "normalised"
DEDUPE_EXACT = "exact"
DEDUPE_HOST = "host"


@dataclass(frozen=True)
class RecordSchema:
    prefix: str
    required: tuple[str, ...]
    optional: tuple[str, ...] = ()
    ref_fields: tuple[str, ...] = ()  # fields whose IDs are references
    union_fields: tuple[str, ...] = ()  # pure ID lists merged by union on dedupe
    allow_empty: tuple[str, ...] = ()
    dedupe: tuple[str, ...] = (TITLE,)
    dedupe_mode: str = DEDUPE_NORMALISED
    section: str | None = "## Records"  # where merge appends; None for record-file kind
    owner_stage: str | None = None  # overrides the artifact's owner stage

    @property
    def fields(self) -> tuple[str, ...]:
        return self.required + self.optional


@dataclass(frozen=True)
class ArtifactSpec:
    path: str  # workspace-relative path or glob
    owner_stage: str
    kind: str
    title: str
    schemas: tuple[RecordSchema, ...] = field(default_factory=tuple)

    def schema(self, prefix: str) -> RecordSchema | None:
        return next((s for s in self.schemas if s.prefix == prefix), None)

    def owner_of(self, prefix: str) -> str:
        sch = self.schema(prefix)
        if sch is not None and sch.owner_stage:
            return sch.owner_stage
        return self.owner_stage

    @property
    def is_glob(self) -> bool:
        return any(ch in self.path for ch in "*?[")

    @property
    def directory(self) -> str:
        return self.path.rsplit("/", 1)[0] if "/" in self.path else ""


def _rs(prefix: str, required: str, **kw: object) -> RecordSchema:
    """Compact constructor: ``required`` is a comma-separated field list."""

    def split(value: object) -> tuple[str, ...]:
        if isinstance(value, tuple):
            return value
        return tuple(x.strip() for x in str(value).split(",") if x.strip())

    for key in ("optional", "ref_fields", "union_fields", "allow_empty", "dedupe"):
        if key in kw:
            kw[key] = split(kw[key])
    req = split(required)
    if "Confidence" in req:
        # §11: INFERRED needs "Derived from", UNKNOWN needs "Related unknown" — so every
        # confidence-bearing schema accepts both as optional, unioned reference lists.
        for name in CONFIDENCE_SUPPORT_FIELDS:
            for key in ("optional", "ref_fields", "union_fields"):
                current = split(kw.get(key, ()))
                if name not in current and not (key == "optional" and name in req):
                    kw[key] = (*current, name)
    return RecordSchema(prefix, req, **kw)  # type: ignore[arg-type]


D, PM, SD, AL, PP = (
    stages.DISCOVERY,
    stages.PRODUCT_MODEL,
    stages.SCOPE_DEFINED,
    stages.ARCHITECTURE_LOCKED,
    stages.PHASE_PLAN_READY,
)

CATALOG: tuple[ArtifactSpec, ...] = (
    # ---- DISCOVERY -------------------------------------------------------------------
    ArtifactSpec(
        "research/sources.md",
        D,
        KIND_RECORDS,
        "Sources",
        (
            _rs(
                "S",
                "URL, Canonical URL, Category, Tier, Authority, Relevant area, Published, "
                "Last inspected, Notes",
                optional="Via",
                allow_empty="Notes",
                dedupe="Canonical URL",
                dedupe_mode=DEDUPE_EXACT,
            ),
        ),
    ),
    ArtifactSpec(
        "research/DISCOVERY_LEDGER.md",
        D,
        KIND_RECORDS,
        "Discovery ledger",
        (
            _rs(
                "D",
                "Claim, Evidence, Confidence, Product impact, Engineering impact, Status",
                optional="Derived from, Related unknown, Conflicts, Resolution",
                ref_fields="Evidence, Derived from, Related unknown, Conflicts",
                union_fields="Evidence, Derived from, Related unknown",
                allow_empty="Product impact, Engineering impact",
                dedupe="Claim",
            ),
        ),
    ),
    ArtifactSpec(
        "research/UNKNOWNS.md",
        D,
        KIND_RECORDS,
        "Unknowns",
        (
            _rs(
                "U",
                "Question, Reason it matters, Available evidence, V1 default, Impact, Related",
                ref_fields="Available evidence, Related",
                union_fields="Available evidence, Related",
                allow_empty="V1 default, Related",
                dedupe="Question",
            ),
            _rs(
                "UD",
                "Unknown, V1 default, Rationale, Impact if wrong",
                ref_fields="Unknown",
                dedupe="Unknown",
                dedupe_mode=DEDUPE_EXACT,
                section="## V1 defaults",
                owner_stage=SD,
            ),
        ),
    ),
    ArtifactSpec(
        "research/product-surfaces.md",
        D,
        KIND_RECORDS,
        "Product surfaces",
        (
            _rs(
                "PS",
                "Purpose, Users, Visible capabilities, Related features, Known routes, Evidence, "
                "Confidence, Dependencies, Unanswered questions",
                ref_fields="Related features, Evidence, Unanswered questions",
                union_fields="Evidence, Unanswered questions",
                allow_empty="Related features, Known routes, Dependencies, Unanswered questions",
            ),
        ),
    ),
    ArtifactSpec("research/product-overview.md", D, KIND_DOCUMENT, "Product overview"),
    ArtifactSpec("research/README.md", D, KIND_DOCUMENT, "Research"),
    # ---- PRODUCT_MODEL ---------------------------------------------------------------
    ArtifactSpec(
        "research/FEATURE_MATRIX.md",
        PM,
        KIND_RECORDS,
        "Feature matrix",
        (
            _rs(
                "F",
                "Domain, Feature, Parent, Surface, Evidence, Confidence, Plan tier, Complexity, "
                "Notes",
                optional="Derived from, Related unknown",
                ref_fields="Parent, Surface, Evidence, Derived from, Related unknown",
                union_fields="Evidence, Derived from, Related unknown",
                allow_empty="Parent, Notes",
                dedupe="Domain, Feature",
            ),
        ),
    ),
    ArtifactSpec(
        "research/workflows/W-*.md",
        PM,
        KIND_RECORD_FILE,
        "Workflow",
        (
            _rs(
                "W",
                "Actor, Trigger, Features, Surfaces, Evidence, Confidence, Preconditions, Outcome",
                ref_fields="Features, Surfaces, Evidence",
                union_fields="Features, Surfaces, Evidence",
                allow_empty="Preconditions",
                section=None,
            ),
        ),
    ),
    ArtifactSpec(
        "spec/DOMAIN_MODEL.md",
        PM,
        KIND_RECORDS,
        "Domain model",
        (
            _rs(
                "E",
                "Responsibility, Identity, Relationships, Lifecycle, Mutable fields, "
                "Immutable fields, Deletion semantics, Ownership, Authorization implications, "
                "Evidence, Confidence",
                optional="Derived from, Related unknown, Features, Human-readable key, "
                "Stable after creation",
                ref_fields="Relationships, Evidence, Derived from, Related unknown, Features",
                union_fields="Evidence, Derived from, Related unknown, Features",
            ),
        ),
    ),
    ArtifactSpec(
        "spec/PERMISSIONS_MATRIX.md",
        PM,
        KIND_RECORDS,
        "Permissions matrix",
        (
            _rs(
                "RL",
                "Description, Scope, Inherits, Evidence, Confidence",
                ref_fields="Inherits, Evidence",
                union_fields="Evidence",
                section="## Roles",
            ),
            _rs(
                "PR",
                "Resource, Action, Grants, Limited means, Evidence, Confidence",
                optional="Related unknown",
                ref_fields="Resource, Grants, Evidence, Related unknown",
                union_fields="Evidence, Related unknown",
                allow_empty="Limited means",
                section="## Rules",  # title dedupe: a corrected rule supersedes the old one
            ),
        ),
    ),
    ArtifactSpec(
        "spec/INTEGRATIONS.md",
        PM,
        KIND_RECORDS,
        "Integrations",
        (
            _rs(
                "I",
                "Purpose, Direction, Authentication, Events, Data exchanged, User configuration, "
                "Failure behaviour, Sync requirements, Evidence, Confidence",
                optional="Provider category, Plan tier",
                ref_fields="Evidence",
                union_fields="Evidence",
            ),
        ),
    ),
    ArtifactSpec(
        "research/architecture-inference.md",
        PM,
        KIND_RECORDS,
        "Architecture inference",
        (
            _rs(
                "A",
                "Area, Observation, Evidence, Confidence, Engineering implication, "
                "Target implementation, Our requirement, Derived from",
                ref_fields="Evidence, Derived from",
                union_fields="Evidence, Derived from",
                dedupe="Observation",
            ),
            _rs(
                "AP",
                "Inference, Proposed implementation, Decision",
                ref_fields="Inference, Decision",
                dedupe="Inference",
                dedupe_mode=DEDUPE_EXACT,
                section="## Proposals",
                owner_stage=AL,
            ),
        ),
    ),
    ArtifactSpec(
        "research/COMPETITORS.md",
        PM,
        KIND_RECORDS,
        "Competitors",
        (
            _rs(
                "C",
                "Name, URL, Positioning, Target users, Pricing model, Table-stakes features, "
                "Differentiators, Common complaints, Evidence, Confidence",
                ref_fields="Table-stakes features, Common complaints, Evidence",
                union_fields="Table-stakes features, Evidence",  # a re-run adds offered features
                dedupe="URL",
                dedupe_mode=DEDUPE_HOST,
            ),
            _rs(
                "FS",
                "Feature, Signal, Competitors, Evidence, Notes",
                ref_fields="Feature, Competitors, Evidence",
                union_fields="Competitors, Evidence",
                allow_empty="Notes",
                dedupe="Feature, Signal",
                dedupe_mode=DEDUPE_EXACT,
                section="## Feature signals",
            ),
        ),
    ),
    # ---- SCOPE_DEFINED ---------------------------------------------------------------
    ArtifactSpec(
        "spec/PARITY_MATRIX.md",
        SD,
        KIND_RECORDS,
        "Parity matrix",
        (
            _rs(
                "SC",
                "Feature, Core value, User frequency, Dependency importance, Differentiation, "
                "Engineering complexity, Infrastructure complexity, Security impact, "
                "Operational cost, Time to implement, External availability, Future",
                optional="Override decision, Override reason, Simplification, External service",
                ref_fields="Feature",
                dedupe="Feature",
                dedupe_mode=DEDUPE_EXACT,
                section="## Scores",
            ),
        ),
    ),
    ArtifactSpec(
        "spec/PRODUCT_SPEC.md",
        SD,
        KIND_RECORDS,
        "Product specification",
        (
            _rs(
                "R",
                "Statement, Derived from, Acceptance signal, Priority, Features",
                ref_fields="Derived from, Features",
                union_fields="Derived from, Features",
                dedupe="Statement",
                section="## Requirements",
            ),
        ),
    ),
    # ---- ARCHITECTURE_LOCKED ---------------------------------------------------------
    ArtifactSpec(
        "spec/ARCHITECTURE.md",
        AL,
        KIND_RECORDS,
        "Architecture",
        (
            _rs(
                "INV",
                "Rule, Reason, Enforced by, Derived from",
                ref_fields="Derived from",
                union_fields="Derived from",
                dedupe="Rule",
                section="## Invariants",
            ),
        ),
    ),
    ArtifactSpec(
        "spec/decisions/ADR-*.md",
        AL,
        KIND_RECORD_FILE,
        "Architecture decision",
        (
            _rs(
                "ADR",
                "Context, Decision, Alternatives, Reason, Trade-offs, Satisfies, Status",
                optional="Topic",
                ref_fields="Satisfies",
                union_fields="Satisfies",
                section=None,
            ),
        ),
    ),
    # ---- PHASE_PLAN_READY ------------------------------------------------------------
    ArtifactSpec("README.md", PP, KIND_DOCUMENT, "README"),
    ArtifactSpec("IMPLEMENTATION_PLAN.md", PP, KIND_DOCUMENT, "Implementation plan"),
    ArtifactSpec("CLAUDE.md", PP, KIND_DOCUMENT, "CLAUDE.md"),
    ArtifactSpec("DEVELOPMENT.md", PP, KIND_DOCUMENT, "Development"),
    ArtifactSpec("STARTUP_PROMPT.md", PP, KIND_DOCUMENT, "Startup prompt"),
    ArtifactSpec("plans/README.md", PP, KIND_DOCUMENT, "Phase plans"),
    ArtifactSpec("plans/phase-*.md", PP, KIND_DOCUMENT, "Phase"),
    ArtifactSpec("spec/TRACEABILITY.md", PP, KIND_DOCUMENT, "Traceability"),
)


# Well-known artifacts other modules read by name.
OVERVIEW_PATH = "research/product-overview.md"
FEATURE_MATRIX_PATH = "research/FEATURE_MATRIX.md"
SURFACES_PATH = "research/product-surfaces.md"
RESEARCH_README_PATH = "research/README.md"
DOMAIN_MODEL_PATH = "spec/DOMAIN_MODEL.md"
PERMISSIONS_PATH = "spec/PERMISSIONS_MATRIX.md"
INTEGRATIONS_PATH = "spec/INTEGRATIONS.md"
INFERENCE_PATH = "research/architecture-inference.md"
COMPETITORS_PATH = "research/COMPETITORS.md"
UNKNOWNS_PATH = "research/UNKNOWNS.md"
PARITY_PATH = "spec/PARITY_MATRIX.md"
PRODUCT_SPEC_PATH = "spec/PRODUCT_SPEC.md"
ARCHITECTURE_PATH = "spec/ARCHITECTURE.md"
IMPLEMENTATION_PLAN_PATH = "IMPLEMENTATION_PLAN.md"
PLANS_README_PATH = "plans/README.md"
PHASES_GLOB = "plans/phase-*.md"
ROOT_DOCS = (
    "README.md",
    "IMPLEMENTATION_PLAN.md",
    "CLAUDE.md",
    "DEVELOPMENT.md",
    "STARTUP_PROMPT.md",
)
# Workspace folders a generated phase may touch besides the declared repository tree.
WORKSPACE_ROOTS = ("research/", "spec/", "plans/")

# Closed value sets per (prefix, field), checked by validators (BAD_ENUM).
ENUMS: dict[tuple[str, str], tuple[str, ...]] = {
    ("F", "Complexity"): ("Low", "Medium", "High"),
    ("F", "Plan tier"): ("all", "paid", "enterprise", "unknown"),
    ("U", "Impact"): ("Low", "Medium", "High"),
    ("E", "Stable after creation"): ("yes", "no", "unknown"),
    ("RL", "Scope"): ("workspace", "team", "resource", "system"),
    ("I", "Direction"): ("inbound", "outbound", "bidirectional"),
    ("I", "Provider category"): ("scm", "chat", "calendar", "identity", "storage", "email",
                                 "analytics", "payments", "webhooks", "api", "other"),
    ("SC", "Future"): ("yes", "maybe", "no"),
    ("SC", "Override decision"): ("BUILD NOW", "BUILD SIMPLIFIED", "USE EXTERNAL SERVICE", "DEFER",
                                  "DROP"),
    ("R", "Priority"): ("must", "should"),
    ("ADR", "Topic"): ("identity", "tenancy", "authn", "authz", "storage", "realtime", "async",
                       "search", "files", "deployment", "other"),
    ("FS", "Signal"): ("table-stakes", "differentiator", "rare", "absent-in-target"),
    ("A", "Area"): ("realtime", "async", "search", "storage", "files", "authn", "authz", "tenancy",
                    "integrations", "notifications", "audit", "offline", "performance",
                    "availability", "security", "observability", "other"),
}  # fmt: skip

# Fields that must not appear on a record type (FIELD_NOT_YET_ALLOWED), with the reason.
RESERVED_FIELDS: dict[str, tuple[tuple[str, ...], str]] = {
    "F": (
        ("MVP", "Decision", "Score", "Scores", "Override reason", "Override decision"),
        "scoring belongs in SC score cards during SCOPE_DEFINED, not on features",
    ),
    "SC": (
        ("Priority", "Score", "Total", "Decision"),
        "pf.py score computes priorities and decisions; the score card holds only the 0–3 scores",
    ),
    "A": (
        ("Proposed implementation",),
        "our implementation is proposed in AP records during ARCHITECTURE_LOCKED",
    ),
}

# Directories every new workspace starts with (``pf.py init``).
SCAFFOLD_DIRS: tuple[str, ...] = ("research", "spec/decisions", "plans")

# Template files (relative to the skill's templates/ dir) whose name differs from the
# canonical artifact they render.
TEMPLATE_ALIASES: dict[str, str] = {
    "research/research-README.md": "research/README.md",
    "plans/plans-README.md": "plans/README.md",
    **{f"project/{name}": name for name in ROOT_DOCS},
}


def _normalise_rel(path: str) -> str:
    rel = path.replace("\\", "/")
    while rel.startswith("./"):
        rel = rel[2:]
    return rel


def spec_for_path(path: str) -> ArtifactSpec | None:
    """Spec for a workspace-relative canonical path (exact paths win over globs)."""
    rel = _normalise_rel(path)
    for spec in CATALOG:
        if not spec.is_glob and spec.path == rel:
            return spec
    for spec in CATALOG:
        if (
            spec.is_glob
            and fnmatch.fnmatchcase(rel, spec.path)
            and "/" not in rel[len(spec.directory) + 1 :]
        ):
            return spec
    return None


def spec_for_staged_path(path: str) -> ArtifactSpec | None:
    """Like ``spec_for_path`` but record-file artifacts match any ``.md`` in their directory
    (agents may name staged workflow/ADR files freely; merge assigns the final name)."""
    spec = spec_for_path(path)
    if spec is not None:
        return spec
    rel = _normalise_rel(path)
    directory, _, name = rel.rpartition("/")
    for candidate in CATALOG:
        if (
            candidate.kind == KIND_RECORD_FILE
            and candidate.directory == directory
            and name.endswith(".md")
        ):
            return candidate
    return None


def specs_for_stage(stage: str) -> list[ArtifactSpec]:
    """Artifacts owned by ``stage`` (artifact-level ownership)."""
    if stage not in stages.ORDER:
        raise UsageError(f"unknown stage {stage!r}", code="UNKNOWN_STAGE")
    return [s for s in CATALOG if s.owner_stage == stage]


def schemas_for_stage(stage: str) -> list[tuple[ArtifactSpec, RecordSchema]]:
    """Record schemas whose records are owned by ``stage`` (honours per-schema overrides)."""
    return [(a, s) for a in CATALOG for s in a.schemas if (s.owner_stage or a.owner_stage) == stage]


def specs_for_prefix(prefix: str) -> list[ArtifactSpec]:
    return [a for a in CATALOG if a.schema(prefix) is not None]


def schema_for_prefix(prefix: str) -> tuple[ArtifactSpec, RecordSchema]:
    for a in CATALOG:
        s = a.schema(prefix)
        if s is not None:
            return a, s
    raise UsageError(f"no artifact holds records with prefix {prefix!r}", code="UNKNOWN_PREFIX")


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(title: str, max_len: int = 60) -> str:
    slug = _SLUG_RE.sub("-", title.lower()).strip("-")
    return slug[:max_len].rstrip("-") or "untitled"


def record_file_path(spec: ArtifactSpec, record_id: str, title: str) -> str:
    """Canonical path for a record-file record, e.g. research/workflows/W-007-create-task.md."""
    if spec.kind != KIND_RECORD_FILE:
        raise UsageError(f"{spec.path} is not a record-file artifact")
    return f"{spec.directory}/{record_id}-{slugify(title)}.md"
