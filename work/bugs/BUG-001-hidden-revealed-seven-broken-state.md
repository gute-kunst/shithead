# BUG-001 Hidden revealed 7 can strand the game state

## Status

- `done`

## Summary

When a hidden card reveal turns up a 7, the game can enter a broken state if that revealed 7 is not eligible on the current pile. The UI shows the `higher / lower` decision for a revealed 7, but the player cannot resolve it and also does not get a `Take pile` path, so the turn is stuck.

## Current Behavior

- A player reveals a hidden card.
- The hidden card is a 7.
- The screen shows the `7 or higher` / `7 or lower` choice flow.
- The player cannot finish the action.
- The player also does not see a `Take pile` action.
- The table is left in a stranded state.

## Expected Behavior

- Revealing a hidden 7 should never leave the player without a legal way forward.
- If the revealed 7 is legally playable, the player should be able to resolve the `higher / lower` choice and continue normally.
- If the revealed 7 is not legally playable on the current pile, the system should force the correct fallback path, which is likely taking the pile, and the UI must expose that state clearly.

## Reproduction

1. Reach a state where the active player must reveal a hidden card.
2. Make the hidden card a 7.
3. Ensure the current pile state makes that revealed 7 ineligible to play.
4. Reveal the hidden card.
5. Observe that the UI shows the `higher / lower` choice, but the turn cannot be completed and no `Take pile` action appears.

## Scope

- In scope:
  - hidden card reveal flow for special rank 7
  - server state transition after revealing an ineligible hidden 7
  - client rendering of the pending resolution / take-pile fallback
- Out of scope:
  - unrelated hidden card bugs
  - general reconnect behavior
  - non-hidden 7 play flow unless needed to align behavior

## Affected Areas

- `server/pyshithead/models/session/manager.py`
- `server/pyshithead/static/app.js`
- `server/tests/test_alpha_api.py`
- possibly `server/pyshithead/debug_presets.py` if a dedicated repro preset is useful

## Acceptance Criteria

- Revealing a hidden 7 no longer strands the turn.
- The server exposes a valid next action for both legal and illegal hidden-7 cases.
- The client shows the correct action state:
  - `higher / lower` only when the revealed 7 can actually be resolved
  - `Take pile` when the revealed 7 must fall back to taking the pile
- A regression test covers the broken scenario.

## Verification

- Server test command:
  `cd server && poetry run python -m pytest tests/test_alpha_api.py -q`
- Browser smoke command:
  `cd server && poetry run python -m pytest tests_browser/test_debug_presets.py tests_browser/test_browser_smoke.py -q -o addopts=''`
- Extra reproduction or debug preset notes:
  - existing `revealed-seven` and hidden-card debug flows are relevant starting points

## Notes

- Likely root cause: the hidden-card flow currently routes all revealed 7s through the same pending high/low resolution path before fully validating whether the revealed card is actually eligible on the current pile.
- Relevant UI strings already exist in `app.js` for pending revealed 7 handling, so the server/client contract around `pending_joker_selection` vs `pending_hidden_take` is the first thing to inspect.
- Fixed by changing the server hidden-card reveal branch so an ineligible hidden 7 now enters `pending_hidden_take` instead of `pending_joker_selection`, with a regression test covering the broken case.
