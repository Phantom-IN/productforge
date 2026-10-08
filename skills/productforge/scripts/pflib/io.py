"""File and output helpers shared by every ``pf.py`` subcommand."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, TextIO


def atomic_write_text(path: str | os.PathLike[str], text: str) -> None:
    """Write ``text`` to ``path`` atomically (UTF-8, no newline translation).

    The content goes to a temporary file in the same directory, is flushed and
    fsynced, then moved over the target with ``os.replace``. Readers therefore see
    either the old or the new content, never a partial file. The temporary file is
    removed if anything fails. The parent directory must already exist.
    """
    target = Path(path)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def _human(obj: Any, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(obj, dict):
        lines = []
        for key, value in obj.items():
            if isinstance(value, (dict, list)) and value:
                lines.append(f"{pad}{key}:")
                lines.append(_human(value, indent + 1))
            else:
                lines.append(f"{pad}{key}: {_scalar(value)}")
        return "\n".join(lines)
    if isinstance(obj, list):
        return "\n".join(
            f"{pad}-\n{_human(item, indent + 1)}"
            if isinstance(item, (dict, list)) and item
            else f"{pad}- {_scalar(item)}"
            for item in obj
        )
    return f"{pad}{_scalar(obj)}"


def _scalar(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, (dict, list)):
        return "none"
    return str(value)


def emit(obj: Any, as_json: bool, stream: TextIO | None = None) -> None:
    """Print ``obj`` as pretty JSON (machine output) or as indented key/value text."""
    out = stream if stream is not None else sys.stdout
    if as_json:
        out.write(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    else:
        out.write(_human(obj) + "\n")
