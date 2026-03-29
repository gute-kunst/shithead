# Architecture

## Overview

The current alpha is a single FastAPI service that serves a browser client and keeps game sessions in memory.

- `server/pyshithead/main.py` exposes the REST endpoints, the per-game WebSocket, and the static app shell.
- `server/pyshithead/models/session` owns lobby/session state, player connectivity, snapshots, reconnects, and timeout handling.
- `server/pyshithead/models/common/game_manager.py` adapts transport-layer requests into game-engine calls.
- `server/pyshithead/models/game` contains the actual Shithead rules, card state, turn order, and play-pile behavior.
- `server/pyshithead/static` contains the browser alpha client, CSS, manifest, and service worker.

## Runtime Flow

### Create / Join / Restore

1. `POST /api/games` creates an in-memory `GameSession` and returns:
   - invite code
   - player token
   - seat
   - full public snapshot
   - seat-scoped private state
1. `POST /api/games/{invite_code}/join` adds another seat while the session is still in `LOBBY`.
1. `POST /api/games/{invite_code}/restore` reclaims an existing seat by player token.

### Live Sync

1. The browser opens `WS /api/games/{invite_code}/ws?token=...`.
1. `GameSession.connect()` binds the socket to the player seat.
1. The server sends:
   - `session_snapshot`
   - `private_state`
1. Every later action is processed through the same session and rebroadcast as updated snapshot/private-state events.

### Game Start And Turn Processing

1. The host starts the game through `POST /api/games/{invite_code}/start`.
1. `GameSession.start()` creates a `GameManager`, which initializes the game engine and deals cards.
1. Browser actions are sent over the WebSocket as typed `ActionRequest` payloads.
1. `GameSession.apply_action()` converts them into engine requests, updates pending-joker state/status messaging, and broadcasts fresh state.

## Important Alpha Constraints

- Sessions are intentionally in-memory only. Deploys, restarts, or service spin-downs can end live games.
- Session snapshots are the source of truth for the browser UI. The client stores only reconnect/seat metadata in `localStorage`.
- Disconnect handling is server-side:
  - short disconnect timeout for the current turn
  - longer idle-session reaping when nobody is connected
- The browser alpha is the supported product surface. The Python terminal client in `client_py` is legacy and should not be treated as the current runtime architecture.
