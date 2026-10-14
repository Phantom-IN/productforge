"""Observe ingestion (v2 phase 03): a redacted session → summary → a Tier 1 source + OB records."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from pflib import merge, observe, records, state, trace, validators, workspace
from pflib.index import WorkspaceIndex

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "observe-session"
SID = "obs-20261014-140548"
PREFIX = f".productforge/observe/{SID}"


def with_session(ws: Path) -> Path:
    shutil.copytree(FIXTURE / SID, observe.observe_root(ws) / SID)
    return ws


def test_summary_is_deterministic_and_matches_the_snapshot() -> None:
    first = observe.summarise(FIXTURE / SID, PREFIX)
    assert first == observe.summarise(FIXTURE / SID, PREFIX)
    expected = json.loads((FIXTURE / "summary.expected.json").read_text(encoding="utf-8"))
    assert first == expected


def test_summary_content() -> None:
    s = observe.summarise(FIXTURE / SID, PREFIX)
    assert [x["route"] for x in s["screens"]] == ["/", "/tasks", "/tasks/:id", "/settings"]
    assert {(e["method"], e["route"]) for e in s["endpoints"]} >= {
        ("POST", "/api/session"), ("GET", "/api/tasks"), ("POST", "/api/tasks"),
        ("POST", "/graphql"), ("GET", "/api/members"), ("GET", "/api/settings"),
    }  # fmt: skip
    (perm,) = s["permissions"]
    assert perm["status"] == 403 and perm["after"] == "click · link “Settings” on /tasks"
    assert [step["label"] for step in s["steps"]] == [None, "Open a task", "Open settings"]
    assert s["realtime"][0]["channel"] == "/ws" and len(s["realtime"][0]["received"]) == 2


def ingested(ws: Path) -> dict[str, object]:
    return observe.ingest(with_session(ws), SID)


def test_ingest_creates_one_tier1_source_and_its_observations(tasklet_discovery: Path) -> None:
    ws = tasklet_discovery
    out = ingested(ws)
    index = WorkspaceIndex(ws)
    src = next(r for _, r in index.records("S") if r.id == out["source"])
    assert src.get("Category") == "observed-session" and src.get("Tier") == "1"
    obs = [r for _, r in index.records("OB")]
    assert len(obs) == out["observations"] == 26
    assert {r.get("Kind") for r in obs} == set(observe_kinds())
    assert all(records.parse_refs(r.get("Evidence")) == [out["source"]] for r in obs)
    assert (observe.observe_root(ws) / SID / observe.SUMMARY).is_file()
    assert validators.run(ws) == []


def observe_kinds() -> tuple[str, ...]:
    from pflib.validators import observations

    return observations.KINDS


def test_reingesting_adds_nothing(tasklet_discovery: Path) -> None:
    ws = tasklet_discovery
    first = ingested(ws)
    again = observe.ingest(ws, SID)
    assert again["source"] == first["source"] and again["new_ids"] == []


def test_ingest_appends_after_discovery_closed(tasklet_product_model: Path) -> None:
    ws = tasklet_product_model
    assert state.load(ws).state.value == "PRODUCT_MODEL"
    ingested(ws)
    assert [f for f in validators.run(ws) if f.severity == "error"] == []


def stage_claim(ws: Path, evidence: str) -> str:
    run_id, path = workspace.create_staging_run(ws, "product-analyst")
    (path / "research").mkdir(parents=True, exist_ok=True)
    (path / "research/DISCOVERY_LEDGER.md").write_text(
        "### D-?1 — Settings are restricted to workspace owners\n"
        "- Claim: A member who opens Settings gets a 403 that names the owner role.\n"
        f"- Evidence: {evidence}\n- Confidence: CONFIRMED\n- Product impact: owner-only settings\n"
        "- Engineering impact: role check on settings endpoints\n- Status: active\n"
    )
    report = merge.merge(ws, run_id)
    return report.id_map["D-?1"]


def test_a_claim_citing_an_observation_is_confirmed_and_explainable(
    tasklet_discovery: Path,
) -> None:
    ws = tasklet_discovery
    out = ingested(ws)
    perm = next(r.id for _, r in WorkspaceIndex(ws).records("OB") if r.get("Kind") == "permission")
    claim = stage_claim(ws, perm)
    assert validators.run(ws) == []  # CONFIRMED reaches the Tier 1 session through the OB
    up = trace.explain(ws, claim)["upstream"]
    assert up[0]["id"] == perm and up[0]["children"][0]["id"] == out["source"]


def test_artifacts_must_exist_unless_the_session_was_discarded(tasklet_discovery: Path) -> None:
    ws = tasklet_discovery
    ingested(ws)
    folder = observe.observe_root(ws) / SID
    shutil.rmtree(folder / "screens")
    missing = {f.code for f in validators.run(ws)}
    assert missing == {"OB_ARTIFACT_MISSING"}
    observe.discard(ws, SID, "done with it")
    assert validators.run(ws) == []


def test_live_sessions_cannot_be_ingested(
    tasklet_discovery: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = with_session(tasklet_discovery)
    monkeypatch.setattr(observe, "pid_alive", lambda pid: True)
    status = observe.observe_root(ws) / SID / "status.json"
    status.write_text(json.dumps({"status": "recording", "pid": 1}))
    with pytest.raises(Exception) as exc:
        observe.ingest(ws, SID)
    assert getattr(exc.value, "code", None) == "OBSERVE_ACTIVE"


def test_page_payloads_are_page_loads_not_endpoints(tmp_path: Path) -> None:
    folder = tmp_path / "obs-20261014-150000"
    folder.mkdir()
    lines = [
        {"seq": 1, "type": "request", "method": "GET", "route": "/websites/:id", "status": 200,
         "resource_type": "fetch", "content_type": "text/x-component"},
        {"seq": 2, "type": "request", "method": "GET", "route": "/api/websites/:id/stats",
         "status": 200, "resource_type": "fetch", "content_type": "application/json",
         "response_shape": {"pageviews": "number"}},
    ]  # fmt: skip
    (folder / "events.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
    s = observe.summarise(folder)
    assert [e["route"] for e in s["endpoints"]] == ["/api/websites/:id/stats"]
    assert s["page_loads"] == [{"route": "/websites/:id", "count": 1}]


def test_generated_observation_titles_are_never_near_duplicates(tasklet_discovery: Path) -> None:
    ws = tasklet_discovery
    ingested(ws)
    titles = [r.title for _, r in WorkspaceIndex(ws).records("OB")]
    assert "Endpoint `GET /api/tasks`" in titles
    assert not [f for f in validators.run(ws) if f.code == "NEAR_DUPLICATE_TITLE"]
