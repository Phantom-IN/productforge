from __future__ import annotations

import json
from pathlib import Path

from conftest import TASKLET

from pflib import gates, state


def failing(ws: Path) -> list[str]:
    return gates.evaluate(ws, "ARCHITECTURE_LOCKED").failing()


def test_passing_fixture_passes_every_condition() -> None:
    report = gates.evaluate(TASKLET / "ARCHITECTURE_LOCKED", "ARCHITECTURE_LOCKED")
    assert report.passed, [r.to_dict() for r in report.results if not r.passed]
    d = {r.id: r.detail for r in report.results}
    assert d["G-AR-REQUIREMENTS-ADDRESSED"] == "all 11 requirements addressed (0 by convention)"
    assert d["G-AR-INVARIANTS"] == "7 invariants, all enforced"
    assert d["G-AR-REPO-STRUCTURE"].startswith("repository structure declares 13 paths")


def test_failing_fixture_lists_exact_failures() -> None:
    assert failing(TASKLET / "ARCHITECTURE_LOCKED_FAILING") == ["G-AR-INVARIANTS"]


def test_open_stack_choice_fails(tasklet_arch: Path) -> None:
    p = tasklet_arch / "spec/ARCHITECTURE.md"
    p.write_text(
        p.read_text().replace(
            "| Files | Stowage (S3-compatible object storage) |", "| Files | TBD |"
        )
    )
    assert set(failing(tasklet_arch)) == {"G-VALIDATE-CLEAN", "G-AR-STACK-COMPLETE"}


def test_gate_passing_fixture_advances_to_phase_plan_ready(pf_cli, tasklet_arch: Path) -> None:  # type: ignore[no-untyped-def]
    code, out, err = pf_cli(
        "advance", "--to", "PHASE_PLAN_READY", "--confirmed", "--workspace", str(tasklet_arch),
        "--json",
    )  # fmt: skip
    assert code == 0, err
    st = state.load(tasklet_arch)
    assert st.state.value == "PHASE_PLAN_READY" and st.locks["ARCHITECTURE_LOCKED"]
    assert json.loads(out)["gate"]["passed"] is True


# ------------------------------------------------------------ build readiness (v3 phase 04)

ARCH = "spec/ARCHITECTURE.md"
NEW = ("G-AR-EXTERNAL-SERVICES", "G-AR-TOOLCHAIN", "G-AR-ENV-CONTRACT")


def edit(ws: Path, old: str, new: str, rel: str = ARCH) -> None:
    p = ws / rel
    text = p.read_text()
    assert old in text, old
    p.write_text(text.replace(old, new, 1))


def details(ws: Path) -> dict[str, str]:
    return {r.id: r.detail for r in gates.evaluate(ws, "ARCHITECTURE_LOCKED").results}


def test_new_conditions_are_declared_and_pass_on_the_fixture() -> None:
    declared = {cid for cid, _, _ in gates.EXPECTED["ARCHITECTURE_LOCKED"]}
    assert set(NEW) <= declared
    d = details(TASKLET / "ARCHITECTURE_LOCKED")
    assert d["G-AR-EXTERNAL-SERVICES"] == "4 external services, each with a vendor ADR"
    assert d["G-AR-TOOLCHAIN"] == "all 9 concerns pinned and verified"
    assert d["G-AR-ENV-CONTRACT"] == "8 variables, 3 local services"


def test_vendor_tbd_fails_external_services(tasklet_arch: Path) -> None:
    edit(tasklet_arch, "| Payments | Payvault | ADR-013 |", "| Payments | TBD | ADR-013 |")
    assert "G-AR-EXTERNAL-SERVICES" in failing(tasklet_arch)
    assert "Payments: vendor is not named" in details(tasklet_arch)["G-AR-EXTERNAL-SERVICES"]


def test_service_adr_must_exist_be_active_and_a_vendor_topic(tasklet_arch: Path) -> None:
    edit(tasklet_arch, "| Payvault | ADR-013 |", "| Payvault | ADR-011 |")
    assert "ADR-011 does not have Topic: vendor" in details(tasklet_arch)["G-AR-EXTERNAL-SERVICES"]
    edit(tasklet_arch, "| Payvault | ADR-011 |", "| Payvault |  |")
    assert "Payments: no ADR cited" in details(tasklet_arch)["G-AR-EXTERNAL-SERVICES"]
    edit(tasklet_arch, "| Payvault |  |", "| Payvault | ADR-099 |")
    assert "ADR-099 is missing or not active" in details(tasklet_arch)["G-AR-EXTERNAL-SERVICES"]


def test_not_applicable_capability_and_none_row(tasklet_arch: Path) -> None:
    edit(tasklet_arch, "| Payments | Payvault | ADR-013 |", "| Payments | TBD | ADR-013 |")
    edit(tasklet_arch, "- search:", "- payments: V1 has no billing\n- search:")
    assert "G-AR-EXTERNAL-SERVICES" not in failing(tasklet_arch)
    text = (tasklet_arch / ARCH).read_text()
    start = text.index("| Capability | Vendor |")
    end = text.index("\n\n", start)
    edit(
        tasklet_arch,
        text[start:end],
        "| Capability | Vendor | ADR | Test stand-in |\n|---|---|---|---|\n| none | | | |",
    )
    assert details(tasklet_arch)["G-AR-EXTERNAL-SERVICES"] == "no external services"


def test_missing_external_services_table_fails(tasklet_arch: Path) -> None:
    text = (tasklet_arch / ARCH).read_text()
    start = text.index("| Capability | Vendor |")
    end = text.index("\n\n", start)
    edit(tasklet_arch, text[start:end], "")
    assert "has no table" in details(tasklet_arch)["G-AR-EXTERNAL-SERVICES"]


def test_toolchain_row_without_verified_date_fails(tasklet_arch: Path) -> None:
    edit(
        tasklet_arch,
        "| 22.11.0 | 2026-10-13 nodejs.org/dist/index.json |",
        "| 22.11.0 | nodejs.org |",
    )
    assert failing(tasklet_arch) == ["G-AR-TOOLCHAIN"]
    assert "runtime: Verified must read" in details(tasklet_arch)["G-AR-TOOLCHAIN"]


def test_toolchain_unpinned_or_missing_concern_fails(tasklet_arch: Path) -> None:
    edit(tasklet_arch, "| 5.6.3 |", "| latest |")
    assert "language: version is not pinned" in details(tasklet_arch)["G-AR-TOOLCHAIN"]
    edit(tasklet_arch, "| latest |", "| TBD |")
    assert "language: version is not pinned" in details(tasklet_arch)["G-AR-TOOLCHAIN"]
    text = (tasklet_arch / ARCH).read_text()
    line = next(ln for ln in text.splitlines() if ln.startswith("| lint |"))
    edit(tasklet_arch, line + "\n", "")
    assert "lint: no row" in details(tasklet_arch)["G-AR-TOOLCHAIN"]


def test_toolchain_concerns_follow_the_config(tasklet_arch: Path) -> None:
    from pflib import config

    config.write_config(tasklet_arch, {"architecture.toolchain_concerns": ["runtime", "cache"]})
    assert "cache: no row" in details(tasklet_arch)["G-AR-TOOLCHAIN"]


def test_empty_environment_table_fails(tasklet_arch: Path) -> None:
    text = (tasklet_arch / ARCH).read_text()
    start = text.index("| Name | Secret |")
    end = text.index("\n\n### Local services", start)
    edit(
        tasklet_arch,
        text[start:end],
        "| Name | Secret | Used by | Development value |\n|---|---|---|---|",
    )
    assert failing(tasklet_arch) == ["G-AR-ENV-CONTRACT"]
    assert "## Environments has no variable rows" in details(tasklet_arch)["G-AR-ENV-CONTRACT"]


def test_environment_tbd_and_missing_local_service_fail(tasklet_arch: Path) -> None:
    edit(tasklet_arch, "| dev-secret-not-real |", "| TBD |")
    assert (
        "AUTHLANE_CLIENT_SECRET: a cell is empty or TBD"
        in details(tasklet_arch)["G-AR-ENV-CONTRACT"]
    )
    text = (tasklet_arch / ARCH).read_text()
    start = text.index("- postgres:")
    end = text.index("\n\n", start)
    edit(tasklet_arch, text[start:end], "")
    assert "lists no service" in details(tasklet_arch)["G-AR-ENV-CONTRACT"]


def test_local_service_needs_an_image_and_a_port(tasklet_arch: Path) -> None:
    edit(tasklet_arch, "- postgres: postgres:16.4, 5432", "- postgres: postgres:16.4")
    assert (
        "local service 'postgres' needs an image and a port"
        in details(tasklet_arch)["G-AR-ENV-CONTRACT"]
    )
