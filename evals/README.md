# Plugin evals

Cases for `claude plugin eval` (on demand — they cost tokens and are not part of `make check`):

| Case | Checks |
|---|---|
| `status-no-workspace` | `/productforge status` asks `pf.py status` and reports that there is no workspace |
| `refused-closed-stage` | a closed stage's command is refused with the `reopen` hint and writes nothing |
| `lint-from-script` | plan questions are answered from `pf.py lint-phases`, not by reading files |

```bash
claude plugin eval . --runs 1 --ablation none --allow-tools "Bash(python3.11:*)" --no-publish
```

Status: written for the documented `prompt.md` + `graders/` layout, **not yet run** — `claude
plugin eval` is in early access and was not available when they were written (v1.1 phase 02).
