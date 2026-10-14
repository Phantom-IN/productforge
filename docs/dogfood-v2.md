# Dogfood v2 — observe mode

Status: **automated part done; the real-product session needs you** (it must be your own account,
and you drive it — ProductForge never does).

## What already ran (synthetic fixture site, no real product)

`tests/observe/` drives the shipped recorder on a local synthetic site (sign-in, a task list, a
form, a detail page, a WebSocket, GraphQL, a members map and a 403 settings page) with a test
stand-in in place of the user, through `Recorder.open` and `pf.py observe start/status/stop`:

| Check | Result |
|---|---|
| Events recorded | navigations, clicks, submits, field changes, requests, realtime messages, errors, screenshots, pause/resume, labels |
| Request/response shapes | captured at the CDP response stage, 0 lost bodies in 15 runs (a sign-in followed by a redirect lost about 1 in 5 before) |
| Secrets typed or served (password, e-mail, JWT, people's names, task titles, a GraphQL literal) found on disk | **0** |
| Ingest of the recorded session | 1 `observed-session` source, 26 `OB` records, 0 errors, 0 warnings |
| Staged observation-pass output | an OB-cited workflow revision, a `?` cell settled by a 403, an API-shape inference: clean; an internals inference: refused (`INTERNALS_FROM_OBSERVATION`) |

## Sign-in note

The first attempt on Umami Cloud used "Sign in with Google", which Google refuses in a browser a
program controls; the session was discarded. ProductForge does not work around that check. The
run used a self-hosted Umami (Docker, synthetic website and traffic) instead.

## Your 10-minute session (the acceptance run)

On a product you have an account for, ideally the one in a ProductForge workspace in DISCOVERY or
PRODUCT_MODEL:

1. `/productforge observe` — it checks the recorder (offers the ~540 MB install), shows the consent
   text and asks.
2. Say what you will do and your account's role; drive the product in the window that opens for
   about ten minutes, naming each step in the panel's "Now doing" box; press Stop.
3. Let it ingest and run the observation passes. Note the before/after `pf.py status` counts it
   reports: workflow steps citing `OB`, inferences with observed API shapes, permission cells
   resolved.
4. **Secret check** — replace the values with ones you typed or saw (your e-mail, a project name,
   a colleague's name) and run it on the session folder it named:

   ```bash
   grep -rlF -e 'you@example.com' -e 'Project Name' -e 'Colleague Name' \
     .productforge/observe/<session> --exclude='*.png' && echo "LEAK" || echo "clean"
   ```

   Screenshots can show what was on screen; before recording, set `"observe.screenshots": "blur"`
   (or `"off"`) in the workspace's `.productforge/config.json` if that matters.
5. `pf.py validate` must report 0 errors. Then `pf.py observe discard <session> --reason "dogfood
   done"` if you do not want to keep the raw files.

Record the counts and the grep result here (aggregates only — never the product's data).
