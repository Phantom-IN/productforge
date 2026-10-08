from __future__ import annotations

import io as std_io
import json
from pathlib import Path

import pytest

from pflib.io import atomic_write_text, emit


def test_atomic_write_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "a.md"
    atomic_write_text(target, "hello\n")
    assert target.read_text(encoding="utf-8") == "hello\n"


def test_atomic_write_replaces_content_and_leaves_no_temp_files(tmp_path: Path) -> None:
    target = tmp_path / "a.md"
    target.write_text("old", encoding="utf-8")
    atomic_write_text(target, "new — ünïcode\r\nline")
    assert target.read_bytes() == "new — ünïcode\r\nline".encode()  # no newline translation
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.md"]


def test_atomic_write_failure_keeps_old_content_and_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "a.md"
    target.write_text("old", encoding="utf-8")

    def boom(src: str, dst: str) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("pflib.io.os.replace", boom)
    with pytest.raises(OSError):
        atomic_write_text(target, "new")
    assert target.read_text(encoding="utf-8") == "old"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.md"]


def test_atomic_write_requires_existing_parent(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        atomic_write_text(tmp_path / "missing" / "a.md", "x")


def test_emit_json_roundtrips() -> None:
    buf = std_io.StringIO()
    obj = {"workspace": None, "counts": {"S": 3}, "items": ["a", "b"]}
    emit(obj, as_json=True, stream=buf)
    assert json.loads(buf.getvalue()) == obj


def test_emit_human_is_key_value_text() -> None:
    buf = std_io.StringIO()
    emit({"workspace": None, "counts": {"S": 3}}, as_json=False, stream=buf)
    assert buf.getvalue() == "workspace: -\ncounts:\n  S: 3\n"
