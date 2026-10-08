"""Read-side index over a workspace's canonical artifacts (paths come from ``catalog``)."""

from __future__ import annotations

from pathlib import Path

from pflib import catalog, ids, records
from pflib.records import Document, Record


class WorkspaceIndex:
    """Lazily parses canonical record artifacts and indexes their records."""

    def __init__(self, ws: Path) -> None:
        self.ws = ws
        self._docs: dict[str, Document] = {}

    def rel_paths(self, spec: catalog.ArtifactSpec) -> list[str]:
        if spec.is_glob:
            return sorted(
                p.relative_to(self.ws).as_posix() for p in self.ws.glob(spec.path) if p.is_file()
            )
        return [spec.path] if (self.ws / spec.path).is_file() else []

    def document(self, rel: str) -> Document:
        if rel not in self._docs:
            text = (self.ws / rel).read_text(encoding="utf-8")
            self._docs[rel] = records.parse_document(text, path=rel)
        return self._docs[rel]

    def records(self, prefix: str) -> list[tuple[str, Record]]:
        """All canonical records with ``prefix`` as ``(relative path, record)`` pairs."""
        out: list[tuple[str, Record]] = []
        for spec in catalog.specs_for_prefix(prefix):
            for rel in self.rel_paths(spec):
                out.extend((rel, r) for r in self.document(rel).records if r.prefix == prefix)
        return out

    def ids(self, prefix: str) -> list[str]:
        return [r.id for _, r in self.records(prefix)]

    def all_ids(self) -> set[str]:
        return {r.id for prefix in ids.PREFIXES for _, r in self.records(prefix)}
