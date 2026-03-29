# Shithead Card Game

Architecture documentation: [docs/architecture.md](docs/architecture.md)
Draw.io diagram: [docs/architecture.drawio](docs/architecture.drawio)

## Mobile Browser Alpha

The server now exposes a playable browser-based private alpha:

- `GET /` serves the mobile-friendly app shell.
- `POST /api/games` creates a lobby and host seat.
- `POST /api/games/{invite_code}/join` joins a lobby.
- `POST /api/games/{invite_code}/start` starts the game.
- `GET /api/games/{invite_code}` returns the public snapshot.
- `WS /api/games/{invite_code}/ws?token=...` streams realtime updates and player actions.

The browser client in `server/pyshithead/static` is the supported alpha surface.
The older terminal client in `client_py` is legacy tooling and does not describe the current browser-session architecture.

## Render Deploy

The repo now includes a Render blueprint at `render.yaml` for a single free web service:

- root directory: `server`
- health endpoint: `GET /healthz`
- start command: `poetry run python -m uvicorn pyshithead.main:app --host 0.0.0.0 --port $PORT`

The current alpha keeps live sessions in memory, so deploys, restarts, or free-tier idle spin-downs can interrupt active games.

## Development

create schema from model in dir `server`:
`python pyshithead/models/common/request_models.py outputfile ../client_py/shithead/request-schema.json`

create client models from schema in dir `client_py`:
`datamodel-codegen --input shithead/request-schema.json --output shithead/model.py --use-default-kwarg`

## Ressources
https://websockets.readthedocs.io/en/stable/intro/tutorial1.html#prerequisites


https://github.com/kthwaite/fastapi-websocket-broadcast/blob/master/app.py
