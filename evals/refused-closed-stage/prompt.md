---
name: a closed stage's command is refused
tags: [orchestrator, stages]
plugins: ["../.."]
runs: 1
max_turns: 8
timeout_seconds: 300
allowed_tools: ["Bash(python3.11:*)", Read]
context:
  add_dirs: ["../../examples/tasklet"]
---
In the ProductForge workspace `tasklet` (examples/tasklet), run `/productforge research`.
