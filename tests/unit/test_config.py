from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pflib import config
from pflib.errors import PFError

DOC = Path(__file__).resolve().parents[2] / "docs" / "configuration.md"


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    (tmp_path / ".productforge").mkdir()
    return tmp_path


def test_defaults_resolve_without_workspace() -> None:
    assert config.resolve("research.max_sources") == 80
    assert config.resolve("scope.weights.core_value") == 3


def test_precedence_cli_over_file_over_default(ws: Path) -> None:
    assert config.resolve("research.min_sources_gate", ws) == 15
    config.write_config(ws, {"research.min_sources_gate": 10})
    assert config.resolve("research.min_sources_gate", ws) == 10
    assert config.resolve("research.min_sources_gate", ws, {"research.min_sources_gate": 3}) == 3
    assert (
        config.resolve("research.min_sources_gate", ws, {"research.min_sources_gate": None}) == 10
    )


def test_write_config_keeps_only_non_default_overrides(ws: Path) -> None:
    config.write_config(ws, {"competitors.max": 3, "quotes.max_words": 25})
    stored = json.loads((ws / ".productforge/config.json").read_text())
    assert stored == {"competitors.max": 3}
    config.write_config(ws, {"competitors.max": 5})
    assert json.loads((ws / ".productforge/config.json").read_text()) == {}


def test_unknown_key_and_bad_types(ws: Path) -> None:
    with pytest.raises(PFError) as info:
        config.resolve("research.nope")
    assert info.value.code == "UNKNOWN_CONFIG_KEY"
    with pytest.raises(PFError) as info:
        config.write_config(ws, {"research.max_sources": "many"})
    assert info.value.code == "BAD_CONFIG_VALUE"
    with pytest.raises(PFError):
        config.write_config(ws, {"research.max_sources": True})  # bool is not an int here
    assert config.coerce("research.request_delay_seconds", 2) == 2.0


def test_bad_config_file(ws: Path) -> None:
    (ws / ".productforge/config.json").write_text("{not json")
    with pytest.raises(PFError) as info:
        config.resolve("competitors.max", ws)
    assert info.value.code == "BAD_CONFIG_FILE"


def test_robots_is_not_configurable() -> None:
    assert not any("robots" in key for key in config.DEFAULTS)


def test_every_key_has_a_description() -> None:
    assert all(spec.description.strip() for spec in config.DEFAULTS.values())


def test_configuration_doc_lists_exactly_the_registered_keys() -> None:
    text = DOC.read_text(encoding="utf-8")
    documented = set(re.findall(r"^\| `([a-z_.]+)` \|", text, re.M))
    assert documented == set(config.DEFAULTS)
    for key, spec in config.DEFAULTS.items():
        assert spec.description in text, key
