---
name: a thin DISCOVERY is blocked and auto starts with research
tags: [orchestrator, gates, auto]
plugins: ["../.."]
runs: 1
max_turns: 10
timeout_seconds: 300
allowed_tools: ["Bash(python3.11:*)", Read]
context:
  add_dirs: ["../../tests/fixtures/workspaces/tasklet/DISCOVERY_FAILING"]
---
The ProductForge workspace `tests/fixtures/workspaces/tasklet/DISCOVERY_FAILING` is a thin, single-pass DISCOVERY. Can its DISCOVERY stage be closed? Name the failing gate conditions. Then, without running anything for real, which command would `pf.py auto start --dry-run` run first?
