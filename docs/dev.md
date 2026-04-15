# Development Guide

## Supported Surface

- The browser app under `server/pyshithead/static` is the supported product surface.
- The session and reconnect logic live in `server/pyshithead/models/session`.
- The rules engine lives in `server/pyshithead/models/game`.
- Browser coverage is Chromium and WebKit on desktop and mobile profiles, with Firefox covered on desktop only because Playwright Firefox does not support mobile emulation.

## Frontend Direction

The frontend has grown past the phase where adding behavior anywhere is acceptable. Keep the current ownership boundaries intact:

- `frontend/session_controller.js` owns transport and session sync.
- `frontend/game_ui_controller.js` owns gameplay interaction flow, legality handling, optimistic gameplay behavior, and shoutout submission/cooldown behavior.
- `frontend/gameplay_ui_state.js` owns derived gameplay UI state.
- `frontend/view/gameplay_screen.js` owns gameplay rendering.
- `app.js` is mostly composition/wiring plus remaining motion and gesture infrastructure, not the owner for new gameplay or shoutout logic.

For medium or large features, do a quick structural fit check before coding. If a change touches gameplay rendering, gameplay derivation, shoutouts, or transport, extend the existing owner first instead of choosing the easiest file. Prefer explicit state/render flow over imperative DOM patching or post-render sync in `app.js`.

If you touch an old hotspot, leave it at least no worse than before. Avoid broad rewrites when a local extension of an existing boundary is enough.

## Bootstrap

From the repo root:

```powershell
.\.githooks\install.cmd
cd server
poetry install
poetry run python -m playwright install chromium firefox webkit
```

## Run

Development server:

```powershell
cd server
poetry run python -m uvicorn pyshithead.main:app --reload
```

Debug preset server:

```powershell
cd server
poetry run python -m pyshithead.debug_server --preset choose-public
```

Useful presets:

- `lobby-2p`
- `choose-public`
- `normal-turn`
- `host-specials`
- `host-specials-lock`
- `host-turn-15`
- `hidden-reveal`
- `hidden-take`
- `hidden-seven-take`
- `revealed-joker`
- `revealed-seven`
- `game-over`

## Verify

Canonical server test pass:

```powershell
cd server
poetry run python -m pytest tests/test_alpha_api.py -q
```

Canonical browser matrix pass:

```powershell
cd server
poetry run python -m pytest tests_browser/test_debug_presets.py tests_browser/test_browser_smoke.py -q -o addopts=''
```

For a faster Chromium-only run that matches the push CI path:

```powershell
cd server
poetry run python -m pytest tests_browser -q -o addopts='' --browser chromium
```

## Pre-Commit Hook

Enable the repo hook path once from the repo root:

```powershell
.\.githooks\install.cmd
```

After that, every `git commit` runs the same black/isort checks as CI before the commit is created.

## Repo Notes

- Session state is persisted in SQLite by default via `DATABASE_URL`, defaulting to `sqlite:///./shithead.db`.
- Presence is transport-based: `is_connected` means the server currently has a live WebSocket.
- Browser snapshots are the source of truth for the UI. The client only keeps reconnect metadata in `localStorage`.
- Host-managed offline removal and reconnect grace behavior are documented in [docs/architecture.md](./architecture.md).
- Bugs and initiatives should be tracked in-repo under [work/INDEX.md](../work/INDEX.md) and [work/STATE.md](../work/STATE.md).
