---
name: lint questions are answered by the script
tags: [orchestrator, plans]
plugins: ["../.."]
runs: 1
max_turns: 8
timeout_seconds: 300
allowed_tools: ["Bash(python3.11:*)", Read]
context:
  add_dirs: ["../../examples/tasklet"]
---
Is the phase plan of the ProductForge workspace `tasklet` (examples/tasklet) valid? How many phases does it have?
