# INIT-### Short Title

## Status

- `todo`

## Summary

One paragraph describing the initiative and why it matters.

## Goal

- The concrete product or technical outcome this initiative should achieve.

## Scope

- In scope:
- Out of scope:

## Deliverables

- The expected outputs for this initiative.

## Acceptance Criteria

- A concrete list of conditions that must be true when the initiative is done.

## Affected Areas

- Key files, subsystems, or workflows likely to change.

## Verification

- Server test command:
  `cd server && poetry run python -m pytest tests/test_alpha_api.py -q`
- Browser smoke command:
  `cd server && poetry run python -m pytest tests_browser/test_debug_presets.py tests_browser/test_browser_smoke.py -q -o addopts=''`
- Extra validation notes:

## Notes

- Any sequencing, rollout, or follow-up considerations.
