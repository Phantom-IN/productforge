# Security

## Network use

Only `pflib/discover.py` touches the network from scripts: it fetches `robots.txt` first, never
requests a disallowed URL, rate-limits itself and identifies itself. Agents fetch public pages with
Claude Code's WebFetch/WebSearch. Tests never use the network.

## Prompt injection

Fetched pages and delegated skill output are **data, never instructions**. Agents are told to
ignore instructions found in content and to flag the source (`possible prompt injection`).
Delegated output lands in `staging/<run>/raw/`, is never merged, and is normalised by a
ProductForge agent into records that cite the original URLs.

## Installs

`pf.py deps install … --confirmed` runs `claude plugin install` only after the user agreed in the
session; without `--confirmed` it prints the command and installs nothing.

## The stage guard hook

`hooks/stage_guard.py` (PreToolUse on Write/Edit/MultiEdit/NotebookEdit) acts only inside a
directory with `.productforge/state.json`. It denies direct writes to canonical record files,
closed-stage artifacts, generated views and `.productforge/` itself, and allows everything else.
It reads the tool payload from stdin, writes nothing, and **fails open** on any internal error so a
bug cannot block a session. Disable it by disabling the plugin.

## What ProductForge never does

Log in, use test accounts, inspect network traffic, download brand assets or screenshots, copy
proprietary code, or quote more than `quotes.max_words` (25) words of a source.

## Reporting

Please report vulnerabilities privately to the maintainer (see `.claude-plugin/plugin.json`)
rather than in a public issue.
