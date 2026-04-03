# Shithead Card Game

Architecture documentation: [docs/architecture.md](docs/architecture.md)
Development guide: [docs/dev.md](docs/dev.md)
Work tracking: [work/INDEX.md](work/INDEX.md)
Draw.io diagram: [docs/architecture.drawio](docs/architecture.drawio)

## Mobile Browser Alpha

The server now exposes a playable browser-based private alpha:

- `GET /` serves the mobile-friendly app shell.
- `POST /api/games` creates a lobby and host seat.
- `POST /api/games/{invite_code}/join` joins a lobby.
- `POST /api/games/{invite_code}/start` starts the game.
- `GET /api/games/{invite_code}` returns the public snapshot.
- `POST /api/games/{invite_code}/players/{seat}/kick` removes an offline non-host player.
- `WS /api/games/{invite_code}/ws?token=...` streams realtime updates and player actions.

The browser client in `server/pyshithead/static` is the supported alpha surface.

Current multiplayer behavior is mobile-friendly by default:

- players are marked offline when their WebSocket drops
- lobby seats stay reserved until the host removes the offline player
- setup-phase seats auto-remove only after 10 minutes
- an offline active turn auto-resolves only after 5 minutes
- public snapshots expose reconnect metadata so the UI can show offline duration and fallback countdowns

## Render Deploy

The repo now includes a Render blueprint at `render.yaml` for a single free web service:

- root directory: `server`
- health endpoint: `GET /healthz`
- start command: `poetry run python -m uvicorn pyshithead.main:app --host 0.0.0.0 --port $PORT`

The current alpha persists session state in SQLite, but deploys, restarts, or free-tier idle spin-downs can still interrupt active games.

## Development

- canonical bootstrap and test commands live in [docs/dev.md](docs/dev.md)
- in-repo work tracking lives in [work/INDEX.md](work/INDEX.md) and [work/STATE.md](work/STATE.md)

## Resources

- https://websockets.readthedocs.io/en/stable/intro/tutorial1.html#prerequisites
- https://github.com/kthwaite/fastapi-websocket-broadcast/blob/master/app.py
