from __future__ import annotations

import json
from pathlib import Path

from pflib import capabilities, summary


def test_summary_uses_script_output_only(tasklet_plan: Path) -> None:
    text = summary.markdown(tasklet_plan)
    assert text.startswith("# tasklet-alt — blueprint summary\n")
    assert (
        "42 observed claims → 31 features → 8 core requirements → 18 V1 capabilities → 13 phases"
        in text
    )
    assert (
        "BUILD NOW: 14 · BUILD SIMPLIFIED: 1 · USE EXTERNAL SERVICE: 3 · DEFER: 11 · DROP: 2"
        in text
    )
    assert (
        "- ADR-008 — Object storage with signed URLs" in text
        and "- 12 — Deployment and hardening" in text
    )
    assert "D-0" not in text  # no claims or quotes — nothing from the research itself


def test_summary_before_planning(tasklet_product_model: Path) -> None:
    text = summary.markdown(tasklet_product_model)
    assert "→ — phases" in text and "## Phases" not in text


def test_cli(pf_cli, tasklet_plan: Path) -> None:  # type: ignore[no-untyped-def]
    code, out, _ = pf_cli("publish-summary", "--workspace", str(tasklet_plan), "--json")
    assert code == 0 and json.loads(out)["markdown"].startswith("# tasklet-alt")


def test_optional_capabilities_degrade_to_none(tmp_path: Path) -> None:
    registry = capabilities.load_registry()
    detections = capabilities.detect(registry, set(), home=tmp_path, plugin_list=[])
    resolved = capabilities.resolve(registry, detections)
    for cap in ("report.publish", "graph.explore"):
        assert resolved[cap].provider == "none" and not resolved[cap].required, cap
