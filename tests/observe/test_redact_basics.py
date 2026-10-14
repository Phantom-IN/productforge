"""Base redaction rules the recorder relies on (v2 phase 01; phase 02 adds the hard corpus)."""

from __future__ import annotations

import redact


def test_headers_are_an_allowlist() -> None:
    h = {"Authorization": "Bearer abc", "Cookie": "sid=1", "Set-Cookie": "sid=1",
         "X-Api-Key": "k", "Content-Type": "application/json",
         "Referer": "https://a.example/u/123?token=xyz"}  # fmt: skip
    assert redact.headers(h) == {"content-type": "application/json",
                                 "referer": "https://a.example/u/:id?token=string"}  # fmt: skip


def test_urls_keep_their_template_not_their_values() -> None:
    assert redact.url("https://a.example/boards/8f14e45f-ceea-467a-9575-0b5b0c3f8f6e/tasks/42"
                      "?page=2&q=milk#top") == ("https://a.example/boards/:id/tasks/:id"
                                                "?page=number&q=string")  # fmt: skip
    assert redact.route("https://a.example/u/ada@tasklet.example") == "/u/:email"


def test_bodies_become_shapes() -> None:
    body = '[{"id": 1, "title": "a", "due": "2026-01-02"}, {"id": 2, "title": "b", "due": null}]'
    assert redact.body("application/json", body) == [
        {"due": "date|null", "id": "number", "title": "string"}
    ]
    assert redact.body("application/x-www-form-urlencoded", "user=ada&pw=secret") == {
        "pw": "string",
        "user": "string",
    }
    assert redact.body("text/html", "<p>hi</p>") == {"kind": "text/html", "bytes": "<100"}


def test_events_never_carry_values() -> None:
    e = redact.event({"type": "change", "name": "Email  of ada@tasklet.example", "value": "x",
                      "fields": [{"name": "Password", "value": "hunter2"}]})  # fmt: skip
    assert "value" not in e and "value" not in e["fields"][0]
    assert e["name"] == "Email of <email>"
