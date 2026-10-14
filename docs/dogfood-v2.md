# Dogfood v2 — observe mode

Status: **done** — the acceptance session ran on 2026-10-14 (results below).

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

## The acceptance session (2026-10-14)

Self-hosted Umami (Docker, synthetic "Demo Shop" website with seeded visits and custom events),
driven by the user as Owner for about 4½ minutes with six "now doing" labels, in a fresh
DISCOVERY workspace:

| | Result |
|---|---|
| Recorded | 392 events: 75 clicks, 3 submits, 185 requests, 79 screenshots; 17 screens; 67 endpoints with request/response shapes (the goal and funnel creation `POST`s included); 0 realtime channels (the live view polls) |
| Ingest | 1 `observed-session` source, 156 `OB` records |
| Passes | claims (57 from docs after a targeted pass), 21 surfaces; **0 validator errors** |
| Secret check | no password value, token, cookie or `Authorization` header anywhere in the session folder |

Labels group, they do not gate capture: a label stays until the next one, so activity done
without setting a new label lands under the previous one.

Fixed from what this session showed:
- clicks on plain text stored that text (a referrer domain, metric values); now only role and
  selector;
- React Server Components page payloads were listed as API endpoints; now page loads;
- React's generated ids (`_r_kc_`) were taken as labels;
- unknowns could not cite observations (`WRONG_REF_TYPE`, needed a repair pass);
- near-duplicate warnings on script-generated OB titles;
- the product analyst re-staged surfaces as copies (their updates were dropped); it now
  supersedes.

Residual: the signed-in user's display name appears where the product shows it in a button (here
`admin`); for a real account that is the user's own name, on their own computer.

## Running your own session

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
