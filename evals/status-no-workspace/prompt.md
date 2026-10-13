---
name: status outside a workspace
tags: [orchestrator]
plugins: ["../.."]
runs: 1
max_turns: 6
timeout_seconds: 300
allowed_tools: ["Bash(python3.11:*)", Read]
---
/productforge status
