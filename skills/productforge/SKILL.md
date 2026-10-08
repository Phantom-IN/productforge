---
name: productforge
description: >-
  Reverse-engineer a public software product from its website and public sources
  into an evidence-backed, implementation-ready project specification (research
  ledger, feature/workflow/domain model with explicit confidence, MVP scope,
  independent architecture, and a Phase Plan Method build plan). Use when the user
  runs /productforge, asks to reverse-engineer a product, wants to "build
  something like <product>", or wants a product spec or build plan from a URL.
  Specification only - never writes application code.
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, WebFetch, WebSearch, TodoWrite, Task
---

# ProductForge

ProductForge turns an existing software product into an evidence-backed, implementation-ready
engineering blueprint. It researches public sources, reconstructs the product (features,
workflows, domain model, permissions) while keeping facts separate from inference, reduces it to a
realistic MVP, designs an independent architecture, and generates a phase-wise plan that a fresh
Claude Code session can execute with `execute phase 00`.

> **Status: scaffolding (v0.1.0).** Only `status` is wired. Every other command is part of the
> v1 plan (`plans/v1/` in the ProductForge repository) and is not available in this build.

## Locating the scripts

All bookkeeping is done by the deterministic CLI shipped with this skill:

```bash
PF="<base directory of this skill>/scripts/pf.py"
# plugin installs: ${CLAUDE_PLUGIN_ROOT}/skills/productforge/scripts/pf.py
python3.11 "$PF" <subcommand> --json
```

Always use `python3.11` — never bare `python3`. If `python3.11` is not found, stop and tell the
user ProductForge needs Python 3.11 (macOS: `brew install python@3.11`).

Never report a number or a state you did not read from `pf.py` output.

## Commands in this build

- `/productforge status` → run `python3.11 "$PF" status --json` and relay the result in one or two
  sentences. In this build it reports that no ProductForge workspace was found.
- Anything else (`/productforge <url>`, `research`, `features`, `workflows`, `model`,
  `competitors`, `scope`, `architect`, `finalize`, `reopen`) → reply that the command is not
  available in this build yet, and stop. Do not attempt the work manually.
