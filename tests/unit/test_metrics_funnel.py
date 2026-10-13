from __future__ import annotations

from pathlib import Path

from pflib import metrics, render


def test_funnel_counts(tasklet_scope: Path) -> None:
    assert metrics.funnel(tasklet_scope) == {
        "observed_claims": 42, "features": 31, "core_requirements": 8, "v1_capabilities": 18,
        "phases": None,
    }  # fmt: skip


def test_funnel_is_rendered_in_the_product_spec(tasklet_scope: Path) -> None:
    body = render.regions((tasklet_scope / "spec/PRODUCT_SPEC.md").read_text())["funnel"]
    assert "| Observed claims | 42 |" in body and "| Phases | — |" in body
    defaults = render.regions((tasklet_scope / "spec/PRODUCT_SPEC.md").read_text())["defaults"]
    assert defaults.count("\n| U-0") == 11


def test_funnel_before_scoping(tasklet_product_model: Path) -> None:
    f = metrics.funnel(tasklet_product_model)
    assert f["core_requirements"] == 0 and f["v1_capabilities"] == 0 and f["features"] == 31
