# GSD Workflow

This repo is ready for `get-shit-done`, but the best results depend on starting from the current supported architecture instead of rediscovering it during execution.

## Recommended Starting Point

Install GSD locally for this repo first, then map the existing codebase before planning new work.

Suggested flow:

```text
npx get-shit-done-cc --local
/gsd:map-codebase
/gsd:new-milestone
```

Use `new-milestone`, not `new-project`, because this repo already has an established codebase, architecture, and test suite.

## Codebase Framing To Keep Stable

When GSD asks about the project, keep these points explicit:

- supported runtime: browser alpha served by the FastAPI app in `server`
- supported client surface: `server/pyshithead/static`
- realtime and reconnect behavior: `server/pyshithead/models/session`
- game rules and turn resolution: `server/pyshithead/models/game`
- verification bar: server tests plus browser smoke tests

## Canonical Verification Commands

Give GSD these exact commands as the default verification path:

```powershell
cd server
poetry run python -m pytest tests/test_alpha_api.py -q
poetry run python -m pytest tests_browser/test_debug_presets.py tests_browser/test_browser_smoke.py -q -o addopts=''
```

## Artifact Policy

Recommended policy for GSD-generated planning state:

- commit milestone and planning artifacts that describe real project intent
- keep specs and execution summaries in git so future planning rounds have stable context
- do not treat generated planning files as throwaway scratch data

In practice, that means keeping files such as these under version control when they are created:

- `PROJECT.md`
- `REQUIREMENTS.md`
- `ROADMAP.md`
- `STATE.md`
- `.planning/`

## Before First Milestone

The repo already has the minimum prep GSD needs:

- architecture docs reflect SQLite-backed sessions and transport-based presence
- root docs point to the supported browser runtime
- canonical bootstrap and test commands are documented in [docs/dev.md](./dev.md)

The next productive step is to run `/gsd:map-codebase` and let GSD index the repo before asking it to plan the next feature milestone.
