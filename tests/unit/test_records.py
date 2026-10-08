from __future__ import annotations

import pytest

from pflib import records
from pflib.records import Record, RecordParseError

DOC = """# Discovery ledger

Intro prose with a reference to S-001 that is not a record.

## Records

### D-041 — Issues may optionally belong to projects
- Claim: Issues may optionally belong to projects.
- Evidence: S-004, S-017
- Confidence: CONFIRMED
- Product impact:
- Engineering impact: issues.project_id must be nullable;
  continuation line one
    deeper indented continuation
- Status: active

### D-052 — Global search spans issues and projects
- Claim: Global search spans issues and projects.
- Evidence: S-021
- Status: active

```markdown
### D-999 — inside a fence, not a record
- Claim: ignored
```

### Notes
Free prose heading, not a record.

## Matrix

| ID | Feature | Notes |
|---|---|---|
| F-001 | Create issue | pipes \\| escaped |
| F-002 | Labels | |
"""


def test_parse_records_fields_and_sections() -> None:
    doc = records.parse_document(DOC)
    assert [r.id for r in doc.records] == ["D-041", "D-052"]
    d41 = doc.records[0]
    assert d41.title == "Issues may optionally belong to projects"
    assert d41.section == "Records"
    assert d41.prefix == "D"
    assert d41.get("Product impact") == ""
    assert d41.get("Engineering impact") == (
        "issues.project_id must be nullable;\ncontinuation line one\n  deeper indented continuation"
    )
    assert d41.order == [
        "Claim",
        "Evidence",
        "Confidence",
        "Product impact",
        "Engineering impact",
        "Status",
    ]
    assert [s.title for s in doc.sections] == ["Discovery ledger", "Records", "Notes", "Matrix"]


def test_round_trip_is_byte_identical() -> None:
    doc = records.parse_document(DOC)
    assert records.serialize_document(doc) == DOC


def test_serialize_record_canonical_form() -> None:
    rec = Record("S-001", "Docs")
    rec.set("URL", "https://x.example")
    rec.set("Notes", "")
    rec.set("Multi", "a\nb")
    assert records.serialize_record(rec) == (
        "### S-001 — Docs\n- URL: https://x.example\n- Notes:\n- Multi: a\n  b\n"
    )


def test_tables_parsed_with_section_and_escaped_pipes() -> None:
    doc = records.parse_document(DOC)
    (table,) = doc.tables
    assert table.section == "Matrix"
    assert table.headers == ["ID", "Feature", "Notes"]
    assert table.rows == [["F-001", "Create issue", "pipes \\| escaped"], ["F-002", "Labels", ""]]


def test_table_round_trip() -> None:
    table = records.parse_table("| a | b |\n|---|---|\n| 1 | 2 |\n")
    assert table is not None
    assert records.serialize_table(table) == "| a | b |\n|---|---|\n| 1 | 2 |\n"
    assert records.parse_table("no table here") is None


def test_append_preserves_existing_content_and_targets_section() -> None:
    new = Record("D-053", "New claim")
    new.set("Claim", "x")
    out = records.append_records(DOC, [new], "## Records")
    assert out.startswith(DOC.split("```markdown")[0])  # everything before is untouched
    doc = records.parse_document(out)
    assert [r.id for r in doc.records] == ["D-041", "D-052", "D-053"]
    assert doc.record("D-053") is not None and doc.record("D-053").section == "Records"
    # the Matrix section and table survive unchanged
    assert out.endswith(DOC.split("## Matrix")[1])
    assert out.replace(records.serialize_record(new) + "\n", "", 1) == DOC


def test_append_creates_missing_section_and_handles_empty_text() -> None:
    rec = Record("S-001", "A")
    rec.set("URL", "u")
    assert records.append_records("# Sources\n", [rec], "## Records") == (
        "# Sources\n\n## Records\n\n### S-001 — A\n- URL: u\n"
    )
    assert records.append_records("", [rec]) == "### S-001 — A\n- URL: u\n"
    two = records.append_records("# T\n", [rec, Record("S-002", "B")])
    assert two == "# T\n\n### S-001 — A\n- URL: u\n\n### S-002 — B\n"


def test_append_never_lands_inside_a_fence() -> None:
    text = "## Records\n\n```\n## Other\n```\n\n## Other\n\nbody\n"
    rec = Record("S-001", "A")
    out = records.append_records(text, [rec], "## Records")
    assert out == "## Records\n\n```\n## Other\n```\n\n### S-001 — A\n\n## Other\n\nbody\n"


@pytest.mark.parametrize(
    "text, line, fragment",
    [
        ("### D-001 - hyphen not em dash\n", 1, "malformed record heading"),
        ("# x\n\n### D-001 — ok\n- Claim no colon\n", 4, "malformed field line"),
        ("### D-001 — ok\n- Claim: a\n- Claim: b\n", 3, "duplicate field"),
        ("### D-001 — a\n\n### D-001 — b\n", 3, "duplicate record id"),
        ("### ZZ-001 — unknown\n", 1, "unknown record prefix"),
    ],
)
def test_parse_errors_report_line_numbers(text: str, line: int, fragment: str) -> None:
    with pytest.raises(RecordParseError) as info:
        records.parse_document(text, path="research/x.md")
    assert info.value.code == "PARSE_ERROR"
    assert info.value.line == line
    assert fragment in info.value.message
    assert info.value.message.startswith(f"research/x.md:{line}:")


def test_parse_refs_known_prefixes_only_and_provisional() -> None:
    value = "S-004, S-017 (pricing), D-?3; UTF-8 COVID-19 E-003 (1:N, required) S-004 W-007-slug"
    assert records.parse_refs(value) == ["S-004", "S-017", "D-?3", "E-003", "W-007"]
    assert records.parse_refs("XS-001 ADR-004 INV-02") == ["ADR-004", "INV-02"]


def test_section_text() -> None:
    doc = records.parse_document(DOC)
    body = doc.section_text("Matrix")
    assert body is not None and body.lstrip().startswith("| ID |")
    assert doc.section_text("Nope") is None


def test_normalise_text() -> None:
    assert (
        records.normalise_text("The Issues, may: belong to PROJECTS!")
        == "issues may belong projects"
    )


def test_shipped_reference_docs_round_trip() -> None:
    from pathlib import Path

    refs = Path(__file__).resolve().parents[2] / "skills" / "productforge" / "references"
    files = sorted(refs.glob("*.md"))
    assert files
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert records.serialize_document(records.parse_document(text, path=path.name)) == text
