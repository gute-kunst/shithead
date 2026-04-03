# Development Guide

## Supported Surface

- The browser alpha under `server/pyshithead/static` is the supported product surface.
- The session and reconnect logic live in `server/pyshithead/models/session`.
- The rules engine lives in `server/pyshithead/models/game`.

## Bootstrap

From the repo root:

```powershell
cd server
poetry install
poetry run python -m playwright install chromium
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
- `revealed-joker`
- `revealed-seven`
- `game-over`

## Verify

Canonical server test pass:

```powershell
cd server
poetry run python -m pytest tests/test_alpha_api.py -q
```

Canonical browser smoke pass:

```powershell
cd server
poetry run python -m pytest tests_browser/test_debug_presets.py tests_browser/test_browser_smoke.py -q -o addopts=''
```

## Repo Notes

- Session state is persisted in SQLite by default via `DATABASE_URL`, defaulting to `sqlite:///./shithead.db`.
- Presence is transport-based: `is_connected` means the server currently has a live WebSocket.
- Browser snapshots are the source of truth for the UI. The client only keeps reconnect metadata in `localStorage`.
- Host-managed offline removal and reconnect grace behavior are documented in [docs/architecture.md](./architecture.md).
- Bugs and initiatives should be tracked in-repo under [work/INDEX.md](../work/INDEX.md) and [work/STATE.md](../work/STATE.md).
