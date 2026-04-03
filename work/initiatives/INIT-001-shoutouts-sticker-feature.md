# INIT-001 Shoutouts / Sticker Feature

## Status

- `in_progress`

## Summary

Add a lightweight table-wide reaction system so players can send a short preset shoutout or sticker-like emotional burst that everyone sees as a live animation near the sender's seat.

## Goal

- Let any connected player react to the table from the lobby or an active game with a small set of preset shoutouts.
- Keep the feature live-only and transient, with no chat history or persistence across reconnects.

## Scope

- In scope:
  - corner shoutout menu in the table UI
  - 6 fixed presets with colorful animated presentation
  - websocket broadcast to connected clients
  - short server-enforced cooldown
  - server/browser regression coverage
- Out of scope:
  - free-text chat
  - sticker uploads or user-generated assets
  - history, replay, or persistence across reconnects
  - moderation/admin tooling

## Deliverables

- New websocket action and live event for shoutouts.
- Table UI control for opening a preset selector and sending a shoutout.
- Animated shoutout rendering anchored to the sender's seat.
- Tests covering snapshot shape, live broadcast, and cooldown rejection.

## Acceptance Criteria

- Players can open the shoutout menu in the lobby and during a game.
- The menu shows the preset shoutouts only.
- Selecting a shoutout broadcasts a live animation to every connected client.
- The shoutout appears near the sender's seat and disappears after a short duration.
- Rapid repeat sends are rejected by the server.
- Shoutouts do not survive refresh, reconnect, or session restore.

## Affected Areas

- `server/pyshithead/models/session/models.py`
- `server/pyshithead/models/session/manager.py`
- `server/pyshithead/main.py`
- `server/pyshithead/static/app.js`
- `server/pyshithead/static/styles.css`
- `server/tests/test_alpha_api.py`
- `server/tests_browser/test_browser_smoke.py`

## Verification

- Server test command:
  `cd server && poetry run python -m pytest tests/test_alpha_api.py -q`
- Browser smoke command:
  `cd server && poetry run python -m pytest tests_browser/test_debug_presets.py tests_browser/test_browser_smoke.py -q -o addopts=''`
- Extra validation notes:
  - confirm shoutouts render for both the sender and a second connected client
  - confirm the server rejects rapid repeats before the cooldown expires

## Notes

- This initiative intentionally stays live-only. Session persistence is limited to the existing game state, not reactions.
- The plan uses the current websocket broadcast path so the implementation stays small and consistent with the rest of the alpha.
