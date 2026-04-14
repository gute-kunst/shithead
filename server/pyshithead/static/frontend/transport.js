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

export function applyAuthPayload(
  payload,
  {
    clearMotionState,
    resetSelection,
    clearRestoreRetryTimer,
    syncKickSeatConfirmation,
    syncTurnNotice,
    persistSession,
    render,
    connectWebSocket,
  },
) {
  clearMotionState();
  state.inviteCode = payload.invite_code;
  state.playerToken = payload.player_token;
  state.seat = payload.seat;
  applySessionSnapshot({ type: "session_snapshot", data: payload.snapshot }, {
    touchPresence: true,
  });
  applyPrivateState({ type: "private_state", data: payload.private_state });
  state.displayName =
    payload.snapshot.players.find((player) => player.seat === payload.seat)
      ?.display_name || state.displayName;
  state.error = "";
  state.restoringSession = false;
  resetSelection();
  clearRestoreRetryTimer();
  state.restoreRetryCount = 0;
  syncKickSeatConfirmation(payload.snapshot);
  persistSession();
  syncTurnNotice(payload.snapshot, { suppress: true });
  render();
  connectWebSocket();
}

export function applyServerSync(payload, handlers = {}) {
  if (payload.type === "session_snapshot") {
    handlers.onSessionSnapshot?.(
      applySessionSnapshot(payload, { touchPresence: true }),
      payload,
    );
    return;
  }

  if (payload.type === "private_state") {
    handlers.onPrivateState?.(applyPrivateState(payload), payload);
    return;
  }

  if (payload.type === "action_error") {
    applyServerError(payload.message);
    handlers.onActionError?.(payload);
    return;
  }

  if (payload.type === "shoutout") {
    handlers.onShoutout?.(payload);
  }
}
