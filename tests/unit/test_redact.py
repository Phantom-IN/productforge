"""observe/redact.py — the rules every observe-mode write passes through (v2 phase 02)."""

from __future__ import annotations

import json

import pytest
import redact

JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjXk"


@pytest.mark.parametrize(
    "header",
    ["Authorization", "Cookie", "Set-Cookie", "X-Api-Key", "X-CSRF-Token", "Proxy-Authorization",
     "X-Amz-Security-Token", "X-Session-Id"],
)  # fmt: skip
def test_secret_headers_never_survive(header: str) -> None:
    assert redact.headers({header: JWT, "Content-Type": "application/json"}) == {
        "content-type": "application/json"
    }


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://app.example/t/42?token=abc#access_token=xyz", "https://app.example/t/:id?token=string"),
        ("https://bob:hunter2@app.example/", "https://app.example/"),
        (f"https://app.example/reset/{JWT}", "https://app.example/reset/:token"),
        ("https://app.example/u/ada%40tasklet.example", "https://app.example/u/:email"),
        ("https://app.example/b/8f14e45f-ceea-467a-9575-0b5b0c3f8f6e", "https://app.example/b/:id"),
        ("https://app.example/docs/2026-release-notes", "https://app.example/docs/2026-release-notes"),
        ("https://app.example/s?q=milk&page=2&on=true&from=2026-01-02",
         "https://app.example/s?q=string&page=number&on=bool&from=date"),
        ("https://app.example/x?ada@tasklet.example=1", "https://app.example/x?:email=number"),
        ("wss://rt.app.example:8443/socket?vsn=2.0.0&key=pk_live_51HxYzAbCdEf12345",
         "wss://rt.app.example:8443/socket?vsn=string&key=string"),
    ],
)  # fmt: skip
def test_urls(url: str, expected: str) -> None:
    assert redact.url(url) == expected


def test_json_becomes_a_stable_shape() -> None:
    a = redact.body(
        "application/json", json.dumps({"b": 1, "a": [{"x": "2026-01-01"}, {"x": None}]})
    )
    b = redact.body("application/json; charset=utf-8",
                    json.dumps({"a": [{"x": None}], "b": 2.5}))  # fmt: skip
    assert a == {"a": [{"x": "date|null"}], "b": "number"}
    assert b == {"a": [{"x": "null"}], "b": "number"}
    assert redact.body("application/json", json.dumps({"token": JWT, "refresh": "r"})) == {
        "refresh": "string",
        "token": "string",
    }


def test_nested_arrays_and_mixed_elements_collapse() -> None:
    body = [[{"id": 1}], [{"id": 2, "tags": ["a", "b"]}], []]
    assert redact.body("application/json", json.dumps(body)) == [
        [{"id": "number", "tags": ["string"]}]
    ]
    assert redact.shape([1, "a", None]) == ["null|number|string"]
    assert redact.shape([{"a": 1}, 3]) == ["mixed"]


def test_data_keys_collapse() -> None:
    body = {"7": {"name": "Ada"}, "ada@tasklet.example": {"seen": True}, "total": 2,
            "8f14e45f-ceea-467a-9575-0b5b0c3f8f6e": {"name": "Grace", "x": None}}  # fmt: skip
    assert redact.shape(body) == {
        "<email>": {"seen": "bool"},
        "<id>": {"name": "string", "x": "null"},
        "total": "number",
    }


def test_graphql_keeps_operation_names_not_variables() -> None:
    q = """
      # Load the board
      query Board($id: ID!, $who: String = "ada@tasklet.example") {
        board(id: $id, filter: "secret phrase") { columns { name } }
        me: viewer { email }
        ... on Query { other }
        stats
      }"""
    op = {"query": q, "variables": {"id": "42", "who": "ada@tasklet.example"}}
    out = redact.body("application/json", json.dumps(op))
    assert out == {"graphql": {"operation": "query", "name": "Board",
                               "fields": ["board", "viewer", "stats"]},
                   "variables": {"id": "number", "who": "string"}}  # fmt: skip
    assert "secret" not in json.dumps(out) and "ada" not in json.dumps(out)
    batch = [
        {"operationName": "A", "query": 'mutation A { addTask(title: "x") { id } }'},
        {"operationName": "B", "extensions": {"persistedQuery": {"sha256Hash": "abc"}}},
    ]
    assert redact.body("application/json", json.dumps(batch)) == [
        {"graphql": {"operation": "mutation", "name": "A", "fields": ["addTask"]}},
        {"graphql": {"persisted": True, "name": "B"}},
    ]


def test_other_bodies() -> None:
    assert redact.body(
        "application/x-www-form-urlencoded", "user=ada&pw=hunter2&remember=true"
    ) == {"pw": "string", "remember": "bool", "user": "string"}
    assert redact.body("text/html", "<p>hi</p>") == {"kind": "text/html", "bytes": "<100"}
    assert redact.body("application/json", "not json {") == {"kind": "application/json",
                                                              "bytes": "<100"}  # fmt: skip
    assert redact.body(None, "") is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Delete 'Plan the sprint'? It cannot be undone.", "Delete <text>? It cannot be undone."),
        ("fetch https://app.example/x?token=abc failed",
         "fetch https://app.example/x?token=string failed"),
        (f"bad token {JWT}", "bad token <token>"),
        ("user ada@tasklet.example from 10.1.2.3 order 12345678",
         "user <email> from <ip> order <number>"),
        ("TypeError: cannot read properties of undefined",
         "TypeError: cannot read properties of undefined"),
    ],
)  # fmt: skip
def test_free_text(raw: str, expected: str) -> None:
    assert redact.text(raw) == expected


def test_events_mask_values_and_item_names() -> None:
    e = redact.event({"type": "change", "name": "Title", "value": "Water the ferns",
                      "fields": [{"name": "Password", "password": "hunter2"}]})  # fmt: skip
    assert e["value_shape"] == {"type": "string", "length": "<100"}
    assert "value" not in e and "hunter2" not in json.dumps(e)
    assert redact.event({"name": "Ada Lovelace", "in_item": True})["name"] == "<item>"
    assert redact.event({"name": "Tasks", "in_item": True, "in_nav": True})["name"] == "Tasks"
    assert redact.collapse([{"name": "<item>"}, {"name": "<item>"}, {"name": "Tasks"}]) == [
        {"name": "<item>", "count": 2},
        {"name": "Tasks"},
    ]
