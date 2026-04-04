# AGENTS.md

## Scope
This repo is a single FastAPI service for the browser-hosted multiplayer Shithead alpha.

Key layers:
- `server/pyshithead/main.py` - REST/WebSocket entrypoint
- `server/pyshithead/models/session/manager.py` - lobby, reconnect, offline, snapshots, multiplayer state
- `server/pyshithead/models/game/` - core card/rules logic
- `server/pyshithead/static/app.js` - browser client
- `server/pyshithead/models/session/store.py` - SQLite persistence
- `render.yaml` - Render deploy

## Rules for agents
- Make the smallest possible change.
- Read only the files directly relevant to the task.
- Do not rescan the whole repo unless necessary.
- Do not refactor large areas without being asked.
- Preserve existing API and websocket payload shapes.

## Where to look first
- Gameplay bug: `models/game/` and `models/session/manager.py`
- Reconnect/offline/lobby bug: `models/session/manager.py`
- UI bug: relevant slice of `static/app.js`
- Deploy bug: `render.yaml`, `server/pyproject.toml`, `main.py`

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
