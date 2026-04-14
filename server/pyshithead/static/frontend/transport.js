import { state } from "./state.js";

export function applySessionSnapshot(payload, { touchPresence = false } = {}) {
  const previousSnapshot = state.snapshot?.data || null;
  state.snapshot = payload;
  if (touchPresence) {
    state.presenceNow = Date.now();
  }
  return {
    previousSnapshot,
    snapshot: payload?.data || null,
  };
}

export function applyPrivateState(payload) {
  const previousPrivateState = state.privateState?.data || null;
  const previousPrivateCards = previousPrivateState?.private_cards || [];
  state.privateState = payload;
  return {
    previousPrivateState,
    previousPrivateCards,
    privateState: payload?.data || null,
  };
}

export function applyServerError(message) {
  state.error = message;
}
