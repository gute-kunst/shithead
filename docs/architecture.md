# Architecture

## Overview

The current app is a single FastAPI service that serves a browser client and persists session state in SQLite.

- `server/pyshithead/main.py` exposes the REST endpoints, the per-game WebSocket, and the static app shell.
- `server/pyshithead/models/session` owns lobby/session state, player connectivity, snapshots, reconnects, and timeout handling.
- `server/pyshithead/models/common/game_manager.py` adapts transport-layer requests into game-engine calls.
- `server/pyshithead/models/game` contains the actual Shithead rules, card state, turn order, and play-pile behavior.
- `server/pyshithead/static` contains the browser client, CSS, manifest, and service worker.

The repo is still compact, but it is no longer in the earliest prototype stage where structure is optional. New frontend work should extend the current ownership boundaries instead of pushing behavior back into the entrypoint file.

## Frontend Ownership

- `server/pyshithead/static/frontend/session_controller.js` owns REST calls, WebSocket lifecycle, session restore/reconnect flow, and inbound snapshot/private-state application.
- `server/pyshithead/static/frontend/game_ui_controller.js` owns gameplay interaction flow, legality handling, optimistic gameplay behavior, and shoutout submission/cooldown behavior.
- `server/pyshithead/static/frontend/gameplay_ui_state.js` owns derived gameplay UI state, prompts, action availability, and turn guidance.
- `server/pyshithead/static/frontend/view/gameplay_screen.js` owns gameplay rendering.
- Shoutouts now move through first-class frontend state and render paths rather than imperative DOM injection.
- `server/pyshithead/static/app.js` is mostly composition/wiring plus remaining motion and gesture infrastructure. That remaining hotspot is not a reason to put new gameplay, shoutout, or transport ownership there.

Practical expectation for feature work:

- use the existing owner module when touching gameplay rendering, gameplay derivation, shoutouts, or transport
- prefer explicit state and rendering flow over post-render DOM patching
- treat real ownership change as an architectural decision, not a casual convenience move
- avoid broad rewrites when a local extension of the current boundary is enough

## Runtime Flow

### Create / Join / Restore

1. `POST /api/games` creates a `GameSession` and returns:
   - invite code
   - player token
   - seat
   - full public snapshot
   - seat-scoped private state
1. `POST /api/games/{invite_code}/join` adds another seat while the session is still in `LOBBY`.
1. `POST /api/games/{invite_code}/restore` reclaims an existing seat by player token.
1. `POST /api/games/{invite_code}/players/{seat}/kick` lets the host remove an offline non-host player.

### Live Sync

1. The browser opens `WS /api/games/{invite_code}/ws?token=...`.
1. `GameSession.connect()` binds the socket to the player seat.
1. The server sends:
   - `session_snapshot`
   - `private_state`
1. Every later action is processed through the same session and rebroadcast as updated snapshot/private-state events.

Presence is transport-based:

- `is_connected` means the server currently has a live websocket for that seat.
- Tab visibility or app backgrounding does not directly change presence.
- Public snapshots include `last_seen_at`, `disconnect_deadline_at`, and `disconnect_action` so the host can see whether the table is waiting for reconnect, waiting for a fallback timeout, or can be unblocked manually.

### Game Start And Turn Processing

1. The host starts the game through `POST /api/games/{invite_code}/start`.
1. `GameSession.start()` creates a `GameManager`, which initializes the game engine and deals cards.
1. Browser actions are sent over the WebSocket as typed `ActionRequest` payloads.
1. `GameSession.apply_action()` converts them into engine requests, updates pending-joker state/status messaging, and broadcasts fresh state.

## Current Constraints

- Sessions are stored in SQLite and can survive a short restart, but deploys or long idle periods can still end live games.
- Session snapshots are the source of truth for the browser UI. The client stores only reconnect/seat metadata in `localStorage`.
- Disconnect handling is server-side:
  - no auto-removal in the lobby
  - 10 minute setup fallback before an offline seat is auto-removed
  - 5 minute active-turn fallback before an offline turn is auto-resolved
  - host-managed removal for offline non-host players
  - longer idle-session reaping when nobody is connected
- The browser app is the supported product surface.
