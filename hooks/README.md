# Hooks

The ProductForge stage guard (`stage_guard.py`, a PreToolUse hook on `Write|Edit|MultiEdit|NotebookEdit`)
arrives in **Phase 16** (IMPLEMENTATION_PLAN.md §2, §17). It will only act inside a directory that
contains `.productforge/state.json`, so ordinary work is never affected.

There is deliberately **no `hooks.json` yet**, so the plugin registers no hooks in this build.
