# AGENTS.md

## Scope
This repo is a single FastAPI service for the browser-hosted multiplayer Shithead app.

The project is no longer in the earliest prototype phase. Speed still matters, but new work should preserve the frontend ownership boundaries established by the refactor series instead of collapsing behavior back into central files.

Key layers:
- `server/pyshithead/main.py` - REST/WebSocket entrypoint
- `server/pyshithead/models/session/manager.py` - lobby, reconnect, offline, snapshots, multiplayer state
- `server/pyshithead/models/game/` - core card/rules logic
- `server/pyshithead/static/frontend/session_controller.js` - REST/WebSocket transport, session sync, inbound session application
- `server/pyshithead/static/frontend/game_ui_controller.js` - gameplay interaction flow, legality handling, optimistic gameplay behavior, shoutout submission/cooldown behavior
- `server/pyshithead/static/frontend/gameplay_ui_state.js` - derived gameplay UI state, prompts, turn guidance
- `server/pyshithead/static/frontend/view/gameplay_screen.js` - gameplay rendering
- `server/pyshithead/static/app.js` - composition/wiring plus remaining motion and gesture infrastructure
- `server/pyshithead/models/session/store.py` - SQLite persistence
- `render.yaml` - Render deploy

## Rules for agents
- Make the smallest possible change.
- Read only the files directly relevant to the task.
- Do not rescan the whole repo unless necessary.
- Do not refactor large areas without being asked.
- Preserve existing API and websocket payload shapes.
- Preserve the current frontend ownership boundaries.
- Put new logic in the owning module first, not the easiest file to reach.
- Do not add new gameplay UI, shoutout UI, or transport/session logic through ad hoc post-render DOM sync in `static/app.js`.
- Prefer explicit state/render flow over imperative DOM patching.
- Distinguish real ownership change from cosmetic file movement.
- If touching old hotspot areas, leave them at least no worse than before.
- Avoid broad rewrites when a local extension of an existing boundary is enough.

## Where to look first
- Gameplay bug: `models/game/` and `models/session/manager.py`
- Reconnect/offline/lobby bug: `models/session/manager.py`
- Transport/session sync UI bug: `static/frontend/session_controller.js`
- Gameplay interaction or shoutout behavior bug: `static/frontend/game_ui_controller.js`
- Derived gameplay prompt/legality/view-model bug: `static/frontend/gameplay_ui_state.js`
- Gameplay rendering bug: `static/frontend/view/gameplay_screen.js`
- App shell, composition, motion, or gesture bug: `static/app.js`
- Deploy bug: `render.yaml`, `server/pyproject.toml`, `main.py`

## Frontend Fit Check

For medium or large frontend work, do a quick structural fit check before coding:
1. transport/session sync belongs in `session_controller.js`
2. gameplay interaction flow and optimistic behavior belong in `game_ui_controller.js`
3. derived gameplay UI state belongs in `gameplay_ui_state.js`
4. gameplay rendering belongs in `view/gameplay_screen.js`
5. `app.js` should not regain gameplay or shoutout decision/rendering ownership

Shoutouts now flow through normal frontend state and renderer ownership. That is the default path for future work too.

## Verification
Run the smallest relevant test slice.

Common commands:
```bash
cd server && poetry run python -m pytest tests/test_alpha_api.py -q
cd server && poetry run python -m pytest tests_browser/test_browser_smoke.py -q -o addopts='' --browser chromium
cd server && poetry run black --check . && poetry run isort --check-only .
```

## Prompt style
When working, start with:
1. diagnosis
2. files to inspect
3. exact verification command

Keep responses concise and repo-specific.
