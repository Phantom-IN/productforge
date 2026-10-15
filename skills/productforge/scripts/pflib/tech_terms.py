"""Technology names that signal a claim about how a product is *built*.

Used only to warn (``TECH_ASSERTION_IN_OBSERVATION``): an observation describes behaviour, and a
target's internals stay UNKNOWN without qualifying evidence. Matching is case-insensitive on word
boundaries; keep entries specific enough not to match ordinary prose.
"""

from __future__ import annotations

import re

TERMS: tuple[str, ...] = (
    # data stores
    "postgres", "postgresql", "mysql", "mariadb", "sqlite", "mongodb", "dynamodb", "cassandra",
    "redis", "memcached", "elasticsearch", "opensearch", "clickhouse", "bigquery", "snowflake",
    "cockroachdb", "firestore", "supabase",
    # messaging and streaming
    "kafka", "rabbitmq", "sqs", "kinesis", "pubsub", "nats",
    # transport and APIs
    "websocket", "websockets", "socket.io", "graphql", "grpc",
    # platforms and runtimes
    "kubernetes", "docker", "aws lambda", "aws", "gcp", "azure", "cloudflare", "heroku", "vercel",
    "node.js", "nodejs", "django", "ruby on rails", "laravel", "elixir", "react.js", "next.js",
    "s3",  # ambiguous words (react, lambda, rails, phoenix) are left out on purpose
)  # fmt: skip

_ALTERNATION = "|".join(re.escape(t) for t in sorted(TERMS, key=len, reverse=True))
_RE = re.compile(r"(?<![\w.])(" + _ALTERNATION + r")(?![\w])", re.I)


def find(text: str) -> list[str]:
    """Technology terms in ``text`` (lower-cased, in order of first appearance, unique)."""
    seen: list[str] = []
    for m in _RE.finditer(text):
        term = m.group(1).lower()
        if term not in seen:
            seen.append(term)
    return seen
