"""Regression tests for the v3 review fixes."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from test_auto import FakeRunner, FakeSleep, events, setup
from test_prompt_contracts import REFERENCES, SKILL
from test_research_plan import entry, scoped, write_cache

import pf
from pflib import (
    auto,
    autonomy,
    config,
    discover,
    discover_rules,
    exclusions,
    gates,
    receipts,
    research,
    state,
    urls,
    validators,
    workspace,
)
from pflib.errors import PFError, UsageError
from pflib.validators import readiness

# -- 1. consent hash on `auto start` ----


def _fake_run(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    seen: list[Path] = []

    def fake(ws: Path, cfg: dict[str, Any], call: Any, **kw: Any) -> dict[str, Any]:
        seen.append(ws)
        return {"completed": True, "stopped": None, "sessions": 0, "retries": 0,
                "stages_passed": [], "decisions": 0, "next_step": "x"}  # fmt: skip

    monkeypatch.setattr(pf.auto, "run", fake)
    return seen


def test_auto_start_confirmed_needs_the_current_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen = _fake_run(monkeypatch)
    ws = tmp_path / "ws"
    base = ["auto", "start", "https://tasklet.example", "--out", str(ws), "--confirmed", "--json"]
    assert pf.main(base) == 2 and not seen and not ws.exists()
    assert pf.main([*base, "--text-sha256", "0" * 64]) == 2 and not seen
    assert not ws.exists()
    err = capsys.readouterr().err
    assert "consent text changed" in err
    assert pf.main([*base, "--text-sha256", autonomy.current_hash(None)]) == 0 and seen == [ws]
    assert autonomy.active(state.load(ws), ws)
    # an active grant needs no hash again (resume)
    assert pf.main(["auto", "start", "--workspace", str(ws), "--confirmed", "--json"]) == 0
    # a stale grant needs one
    st = state.load(ws)
    st.autonomy["text_sha256"] = "stale"
    state.save(ws, st)
    assert pf.main(["auto", "start", "--workspace", str(ws), "--confirmed", "--json"]) == 2


def test_the_hash_follows_permission_args(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_run(monkeypatch)
    ws, _ = setup(tmp_path, "DISCOVERY_FAILING")
    st = state.load(ws)
    st.autonomy = {}
    state.save(ws, st)
    shown = autonomy.current_hash(ws)
    config.write_config(ws, {"auto.permission_args": ["--permission-mode", "plan"]})
    args = ["auto", "start", "--workspace", str(ws), "--confirmed", "--json"]
    assert pf.main([*args, "--text-sha256", shown]) == 2
    assert pf.main([*args, "--text-sha256", autonomy.current_hash(ws)]) == 0


def test_skill_and_reference_pass_the_hash() -> None:
    detail = (REFERENCES / "commands-auto.md").read_text(encoding="utf-8")
    assert (
        "auto start --workspace <ws> [--stack" in detail and "--text-sha256 <text_sha256>" in detail
    )
    assert "--text-sha256" in SKILL.read_text(encoding="utf-8")
    flat = " ".join(detail.split())
    assert "not against something that can write `.productforge/state.json`" in flat


# -- 2. company rule ----


@pytest.mark.parametrize(
    ("path", "category"),
    [
        ("/solutions/legal", "features"),
        ("/pricing/team", "pricing"),
        ("/features/team", "features"),
        ("/legal/security", "security"),
        ("/about", "company"),
        ("/careers/x", "company"),
        ("/privacy", "company"),
        ("/solutions/privacy", "security"),
    ],
)
def test_company_only_as_the_first_path_segment(path: str, category: str) -> None:
    assert discover_rules.classify(f"https://x.example{path}", "x.example") == category


# -- 3. de-duplication in plan() -----------------------------------------------------------------


def test_plan_counts_each_canonical_url_once(tasklet_discovery: Path) -> None:
    ws = tasklet_discovery
    e = entry("https://docs.tasklet.example/a", "docs")
    d = workspace.pf_dir(ws) / workspace.CACHE / "discover"
    d.mkdir(parents=True, exist_ok=True)
    for host in ("a.json", "b.json"):
        (d / host).write_text(json.dumps({"host": host, "entries": [e, e], "external": [e]}))
    plan = research.plan(ws)
    assert next(p for p in plan["partitions"] if p["name"] == "official-docs")["candidates"] == 1
    assert sum(p["candidates"] for p in plan["partitions"]) == 1
    config.write_config(ws, {"research.max_sources": 0})
    assert any("1 candidate URLs" in r for r in research.plan(ws)["scope_reasons"])


# -- 4. resilient readers ----


def test_corrupt_exclusions_is_a_clear_error_and_a_gate_error(tasklet_discovery: Path) -> None:
    ws = tasklet_discovery
    exclusions.path(ws).write_text("{not json", encoding="utf-8")
    with pytest.raises(PFError) as exc:
        exclusions.load(ws)
    assert exc.value.code == "BAD_EXCLUSIONS_FILE"
    exclusions.path(ws).write_text("[1]", encoding="utf-8")
    with pytest.raises(PFError):
        exclusions.load(ws)
    report = gates.evaluate(ws, "DISCOVERY")
    row = next(r for r in report.results if r.id == "G-DISC-SCOPE-DEPTH")
    assert row.status == "error" and "unreadable" in row.detail


def test_read_log_skips_unparsable_lines(tmp_path: Path) -> None:
    ws, _ = setup(tmp_path, "DISCOVERY_FAILING")
    auto.log_event(ws, "one")
    with open(auto.log_path(ws), "a", encoding="utf-8") as handle:
        handle.write("{torn\n")
    auto.log_event(ws, "two")
    assert events(ws) == ["one", "two"]


# -- 5. www hosts ----


def test_page_key_ignores_www_for_comparison_only() -> None:
    assert urls.page_key("https://www.x.example/a/?utm_source=z") == "https://x.example/a"
    assert urls.page_key("https://x.example/a") == urls.page_key("https://www.x.example/a")
    assert urls.canonicalize("https://www.x.example/a") == "https://www.x.example/a"


def test_depth_reads_exclusions_and_nav_treat_www_as_the_same_page(tasklet_discovery: Path) -> None:
    ws = tasklet_discovery
    write_cache(
        ws,
        [
            scoped("https://www.tasklet.example/guide"),
            scoped("https://tasklet.example/nav", nav=True),
        ],
    )
    exclusions.add(ws, ["https://tasklet.example/guide"], "dupe")
    config.write_config(ws, {"research.max_excluded_share": 1.0})
    assert research.depth(ws)["excluded"] == 1
    assert research.nav_unread(ws) == ["https://tasklet.example/nav"]
    exclusions.add(ws, ["https://www.tasklet.example/nav"], "dupe")
    assert research.nav_unread(ws) == []


# -- 6. exclusion abuse ----


def test_exclusions_count_only_up_to_the_share(tasklet_discovery: Path) -> None:
    ws = tasklet_discovery
    pages = [f"https://docs.tasklet.example/p{i}" for i in range(20)]
    write_cache(ws, [scoped(u) for u in pages])
    exclusions.add(ws, pages, "off-scope")
    d = research.depth(ws)
    assert d["excluded"] == 5 and d["excluded_total"] == 20 and d["excluded_uncounted"] == 15
    assert d["needed"] == 7  # ceil(0.6 * 20) - 5
    detail = next(
        r.detail for r in gates.evaluate(ws, "DISCOVERY").results if r.id == "G-DISC-SCOPE-DEPTH"
    )
    assert "15 more exclusions not counted" in detail
    config.write_config(ws, {"research.max_excluded_share": 0.5})
    assert research.depth(ws)["excluded"] == 10
    assert "research.max_excluded_share" in config.DEFAULTS
    assert "`research.max_excluded_share` | `0.25`" in (
        Path(__file__).parents[2] / "docs" / "configuration.md"
    ).read_text(encoding="utf-8")


def test_waive_needs_confirmed_and_status_shows_exclusions(
    pf_cli: Any, tasklet_discovery: Path
) -> None:
    ws = str(tasklet_discovery)
    code, _, err = pf_cli("waive", "competitors", "--reason", "x", "--workspace", ws)
    assert code == 2 and "--confirmed" in err and not state.load(tasklet_discovery).waivers
    code, _, _ = pf_cli("waive", "competitors", "--reason", "x", "--confirmed", "--workspace", ws)
    assert code == 0
    code, _, _ = pf_cli("waive", "competitors", "--revoke", "--workspace", ws)
    assert code == 0
    exclusions.add(tasklet_discovery, ["https://x.example/b"], "dupe")
    data = json.loads(pf_cli("status", "--workspace", ws, "--json")[1])
    assert data["exclusions"] == 1
    assert "Excluded pages: 1" in pf_cli("status", "--workspace", ws)[1]


def test_skill_references_pass_confirmed_to_waive() -> None:
    scope = (REFERENCES / "commands-scope.md").read_text(encoding="utf-8")
    assert '"$PF" waive competitors --reason "<their words>"\n   --confirmed' in scope
    assert "WAIVER_NOT_CONFIRMED" in scope
    gates_doc = (REFERENCES / "stage-gates.md").read_text(encoding="utf-8")
    assert 'waive competitors --reason "…" --confirmed' in gates_doc
    assert "waive competitors --confirmed" in (REFERENCES / "commands-product-model.md").read_text()


# -- 7. auto loop ----


class Scripted(FakeRunner):
    """Returns the scripted return codes in turn (then 0)."""

    def __init__(self, ws: Path, rcs: list[int]) -> None:
        super().__init__(ws)
        self.rcs = list(rcs)

    def __call__(self, argv: list[str], **kw: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append({"argv": argv, **kw})
        return subprocess.CompletedProcess(argv, self.rcs.pop(0) if self.rcs else 0)


def test_the_retry_counter_resets_after_a_successful_session(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY_FAILING", max_retries=2, max_stalls=99, max_sessions=8)
    runner = Scripted(ws, [1, 2, 0, 1, 2, 0, 1])
    summary = auto.run(ws, cfg, pf._inproc(ws), runner, FakeSleep())
    assert "retry limit" not in str(summary["stopped"]) and len(runner.calls) >= 7


def test_the_same_failure_three_times_is_fatal(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY_FAILING", max_retries=24)
    runner = Scripted(ws, [7, 7, 7, 7])
    summary = auto.run(ws, cfg, pf._inproc(ws), runner, FakeSleep())
    assert summary["stopped"] == "repeated failure rc=7" and len(runner.calls) == 3
    ws2, cfg2 = setup(tmp_path / "b", "DISCOVERY_FAILING", max_retries=24, max_sessions=5)
    mixed = Scripted(ws2, [7, 8, 7, 8, 7])
    assert "repeated" not in str(
        auto.run(ws2, cfg2, pf._inproc(ws2), mixed, FakeSleep())["stopped"]
    )


def test_the_wait_is_sliced_and_a_stop_ends_it(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY_FAILING", retry_wait_seconds=40)
    sleep = FakeSleep()
    auto.run(ws, {**cfg, "max_retries": 0}, pf._inproc(ws), Scripted(ws, [1]), sleep)
    assert sleep.waits == []  # the retry limit hit before any wait
    ws2, cfg2 = setup(tmp_path / "b", "DISCOVERY_FAILING", retry_wait_seconds=40)
    sleep2 = FakeSleep()
    auto.run(ws2, cfg2, pf._inproc(ws2), Scripted(ws2, [1, 2, 3]), sleep2)
    assert sleep2.waits[:3] == [15.0, 15.0, 10.0] and max(sleep2.waits) <= 15.0

    ws3, cfg3 = setup(tmp_path / "c", "DISCOVERY_FAILING", retry_wait_seconds=60)
    stops: list[float] = []

    def stopping(seconds: float) -> None:
        stops.append(seconds)
        auto.request_stop(ws3)

    runner = Scripted(ws3, [1, 1])
    summary = auto.run(ws3, cfg3, pf._inproc(ws3), runner, stopping)
    assert stops == [15.0] and len(runner.calls) == 1 and "stop file" in summary["stopped"]


def test_any_oserror_from_the_runner_is_fatal_and_logged(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY_FAILING")

    def denied(argv: list[str], **kw: Any) -> None:
        raise PermissionError("nope")

    summary = auto.run(ws, cfg, pf._inproc(ws), denied, FakeSleep())
    assert "cannot start" in summary["stopped"] and events(ws)[-1] == "stop"


def test_an_unexpected_exception_logs_a_stop_and_reraises(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY_FAILING")

    def boom(argv: list[str], **kw: Any) -> None:
        raise RuntimeError("kaput")

    with pytest.raises(RuntimeError):
        auto.run(ws, cfg, pf._inproc(ws), boom, FakeSleep())
    last = auto.read_log(ws)[-1]
    assert last["event"] == "stop" and "kaput" in last["reason"]


@pytest.mark.parametrize("stack", ['Go "fast"', "it's", "a\nb", "x`y`"])
def test_stack_with_quotes_newlines_or_backticks_is_a_usage_error(
    stack: str, tmp_path: Path
) -> None:
    with pytest.raises(UsageError):
        auto.check_stack(stack)
    ws, cfg = setup(tmp_path, "DISCOVERY")
    with pytest.raises(UsageError):
        auto.session_command(ws, "architect", {**cfg, "stack": stack})
    assert pf.main(["auto", "start", "--workspace", str(ws), "--stack", stack, "--dry-run"]) == 2
    auto.check_stack("Next.js, PostgreSQL 16")


# -- 8. UNDECIDED_CHOICE ----


def _hits(text: str) -> list[tuple[int, str]]:
    pattern = readiness.phrase_pattern(["not chosen", "to be decided", "TBD"])
    assert pattern is not None
    return readiness.undecided_hits(text, pattern)


def test_undecided_phrase_split_across_lines_is_caught() -> None:
    assert _hits("The vendor is not\nchosen yet.\n") == [(1, "not chosen")]
    assert _hits("ok\n\nTo be\n  decided later\n") == [(3, "To be decided")]


def test_fenced_code_and_alternatives_fields_are_skipped() -> None:
    assert _hits("```text\nvendor: TBD\n```\n") == []
    adr = (
        "### ADR-001 — X\n- Topic: vendor\n- Alternatives: Keycloak (not\n  chosen); Auth0\n"
        "- Reason: TBD\n"
    )
    assert _hits(adr) == [(5, "TBD")]  # the Reason line is still checked
    assert _hits("- Alternatives: Keycloak (not chosen)\n\nTBD\n") == [(3, "TBD")]


def test_undecided_choice_ignores_a_rejected_alternative_in_an_adr(tasklet_arch: Path) -> None:
    adr = next((tasklet_arch / "spec/decisions").glob("ADR-012-*.md"))
    text = adr.read_text(encoding="utf-8")
    adr.write_text(text.replace("Keycloak;", "Keycloak (not\nchosen);", 1), encoding="utf-8")
    assert "UNDECIDED_CHOICE" not in [f.code for f in validators.run(tasklet_arch)]


# -- 9. negated use ----


@pytest.mark.parametrize(
    "text",
    [
        "It does not use `ensurePdf` from phase 02.",
        "It never uses the helper from phase 02.",
        "It doesn't call phase 02's helper.",
        "We do not rely on the thing from phase 02.",
    ],
)
def test_negated_use_is_not_a_dependency(text: str) -> None:
    from test_phaselint import CHAIN, _phase, contract_codes

    assert contract_codes(CHAIN[0], _phase("01", "00", text), CHAIN[2]) == []
    positive = text.replace("does not ", "").replace("never uses", "uses")
    positive = positive.replace("doesn't call", "calls").replace("do not rely", "rely")
    assert contract_codes(CHAIN[0], _phase("01", "00", positive), CHAIN[2]) == [
        "PHASE_USES_LATER_PHASE"
    ]


def test_negation_in_another_clause_does_not_hide_a_use() -> None:
    from test_phaselint import CHAIN, _phase, contract_codes

    text = "It does not retry. It uses `ensurePdf` from phase 02."
    assert contract_codes(CHAIN[0], _phase("01", "00", text), CHAIN[2]) == [
        "PHASE_USES_LATER_PHASE"
    ]


# -- 10. ranking ----


def _e(path: str, category: str, nav: bool = False) -> dict[str, Any]:
    url = f"https://x.example{path}"
    return {"url": url, "canonical_url": url, "category": category, "nav": nav}


def test_navigation_never_lifts_a_company_page_and_negative_cap_is_zero() -> None:
    entries = [_e("/about", "company", nav=True), _e("/pricing", "pricing"), _e("/docs/a", "docs")]
    kept, dropped = discover._cap_ranked(entries, 3, {"about", "pricing", "docs"})
    assert kept[-1]["category"] == "company" and dropped == 0
    rr, _ = discover._cap_ranked([dict(e) for e in entries], 3)
    assert rr[-1]["category"] == "company"
    for terms in ({"pricing"}, set()):
        assert discover._cap_ranked([dict(e) for e in entries], -2, terms) == ([], 3)


# -- 11. brief paths ----


def test_brief_inputs_outside_the_workspace_are_ignored(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    run_dir = ws / "run"
    run_dir.mkdir(parents=True)
    (ws / "research").mkdir()
    (ws / "research" / "a.md").write_text("x", encoding="utf-8")
    (tmp_path / "secret.md").write_text("x", encoding="utf-8")
    receipts.save_inputs(
        run_dir,
        ["research/a.md", "../secret.md", "/etc/passwd", f"{ws}/research/a.md", "a/../../x"],
    )
    assert receipts.load_inputs(run_dir, ws) == ["research/a.md", f"{ws}/research/a.md"]
    assert len(receipts.load_inputs(run_dir)) == 5
    found = receipts.check(ws, run_dir, "")
    assert {f["artifact"] for f in found} == {"research/a.md"}
