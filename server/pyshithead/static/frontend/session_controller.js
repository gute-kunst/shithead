import {
  clearPendingLocalPlay,
  clearReconnectTimer,
  clearRestoreRetryTimer,
  hasSavedSession,
  persistSession,
  resetSelection,
  state,
} from "./state.js";
import {
  applyPrivateState,
  applyServerError,
  applySessionSnapshot,
} from "./transport.js";

const restoreUnavailableMessage =
  "Your saved session is no longer available. Join the game again if it is still active.";

function cardId(card) {
  return `${card.rank}-${card.suit}`;
}

function cardMultiset(cards = []) {
  const counts = new Map();
  cards.forEach((card) => {
    const key = cardId(card);
    counts.set(key, (counts.get(key) || 0) + 1);
  });
  return counts;
}

function collectAddedCards(previousCards = [], nextCards = [], limit = Infinity) {
  const counts = cardMultiset(previousCards);
  const added = [];
  nextCards.forEach((card) => {
    const key = cardId(card);
    const remaining = counts.get(key) || 0;
    if (remaining > 0) {
      counts.set(key, remaining - 1);
      return;
    }
    if (added.length < limit) {
      added.push(card);
    }
  });
  return added;
}

function isMyTurn(snapshot = state.snapshot?.data) {
  return snapshot?.current_turn_seat === state.seat;
}

function isPermanentRestoreError(error) {
  return (
    ["auth", "not_found"].includes(error.kind) ||
    [400, 401, 403, 404].includes(error.status)
  );
}

function isShoutoutCooldownOnlyUpdate(previousPrivateData, nextPrivateData) {
  if (!previousPrivateData || !nextPrivateData) {
    return false;
  }
  if (
    previousPrivateData.shoutout_next_available_at ===
    nextPrivateData.shoutout_next_available_at
  ) {
    return false;
  }

  const comparableKeys = [
    "seat",
    "private_cards",
    "pending_joker_selection",
    "pending_joker_card",
    "pending_hidden_take",
  ];

  return comparableKeys.every(
    (key) =>
      JSON.stringify(previousPrivateData[key]) ===
      JSON.stringify(nextPrivateData[key]),
  );
}

export function createSessionController({
  render,
  clearMotionState,
  clearGameStateForLobby,
  clearSession,
  syncKickSeatConfirmation,
  syncTurnNotice,
  closeShoutoutMenu,
  syncShoutoutTriggerState,
  syncShoutoutUnlockTimer,
  detectAnimationEvents,
  appendShoutoutBubble,
  isShoutoutOnCooldown,
  resetKickSeatConfirmation,
  queueLocalMotion,
  shoutoutCooldownMs = 4000,
}) {
  function closeWebSocket({ allowReconnect = false } = {}) {
    clearReconnectTimer();
    state.shouldReconnect = allowReconnect;
    state.wsReady = false;
    state.shoutoutMenuOpen = false;
    const websocket = state.ws;
    state.ws = null;
    if (
      websocket &&
      [WebSocket.OPEN, WebSocket.CONNECTING].includes(websocket.readyState)
    ) {
      websocket.close();
    }
  }

  async function api(path, options = {}) {
    let response;
    try {
      response = await fetch(path, {
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        },
        ...options,
      });
    } catch (error) {
      const requestError = new Error("Could not reach the server.");
      requestError.status = 0;
      requestError.kind = "network";
      throw requestError;
    }

    let data = {};
    try {
      data = await response.json();
    } catch (error) {}

    if (!response.ok) {
      const requestError = new Error(data.detail || "Request failed.");
      requestError.status = response.status;
      if (response.status === 401 || response.status === 403) {
        requestError.kind = "auth";
      } else if (response.status === 404) {
        requestError.kind = "not_found";
      } else if (response.status >= 500) {
        requestError.kind = "server";
      } else {
        requestError.kind = "http";
      }
      throw requestError;
    }
    return data;
  }

  function applyAuthPayload(payload) {
    clearMotionState();
    state.inviteCode = payload.invite_code;
    state.playerToken = payload.player_token;
    state.seat = payload.seat;
    applySessionSnapshot(
      { type: "session_snapshot", data: payload.snapshot },
      { touchPresence: true },
    );
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

  function applyRealtimeSessionSnapshot(payload) {
    const { previousSnapshot, snapshot } = applySessionSnapshot(payload, {
      touchPresence: true,
    });
    detectAnimationEvents(previousSnapshot, snapshot);
    if (!snapshot?.players?.some((player) => player.seat === state.seat)) {
      clearSession(restoreUnavailableMessage);
      return;
    }
    syncKickSeatConfirmation(snapshot);
    syncTurnNotice(snapshot);
    if (snapshot.status === "LOBBY" && previousSnapshot?.status === "GAME_OVER") {
      clearGameStateForLobby();
    }
    if (snapshot.status === "GAME_OVER" || !isMyTurn(snapshot)) {
      resetSelection();
    }
    render();
  }

  function applyRealtimePrivateState(payload) {
    const {
      previousPrivateState,
      previousPrivateCards,
      privateState,
    } = applyPrivateState(payload);
    if (
      state.pendingLocalPlay &&
      Number.isInteger(state.pendingLocalPlay.expectedDrawCount) &&
      state.pendingLocalPlay.expectedDrawCount > 0
    ) {
      state.pendingLocalDrawAnimation = collectAddedCards(
        previousPrivateCards,
        privateState?.private_cards || [],
        state.pendingLocalPlay.expectedDrawCount,
      );
    }
    state.hiddenLocalHandCardIds = [];
    state.pendingLocalPlay = null;
    if (isShoutoutOnCooldown(privateState)) {
      closeShoutoutMenu({ rerender: false });
    }
    if (isShoutoutCooldownOnlyUpdate(previousPrivateState, privateState)) {
      syncShoutoutTriggerState();
      syncShoutoutUnlockTimer();
      return;
    }
    if (privateState?.pending_joker_selection || privateState?.pending_hidden_take) {
      state.selectedCards = [];
      state.jokerRank = privateState?.pending_joker_card?.effective_rank || null;
      state.highLowChoice = "";
    }
    render();
  }

  function handleActionError(message) {
    applyServerError(message);
    clearPendingLocalPlay();
    state.pendingLocalDrawAnimation = null;
    render();
  }

  function scheduleReconnect() {
    clearReconnectTimer();
    if (!state.shouldReconnect || !state.playerToken) {
      return;
    }
    state.reconnectTimer = window.setTimeout(() => {
      state.reconnectTimer = null;
      connectWebSocket();
    }, 1200);
  }

  function scheduleRestoreRetry() {
    if (
      !hasSavedSession() ||
      state.snapshot ||
      state.restoringSession ||
      state.restoreRetryCount >= 3
    ) {
      return;
    }
    clearRestoreRetryTimer();
    const retryDelays = [1500, 4000, 8000];
    const delay =
      retryDelays[state.restoreRetryCount] || retryDelays[retryDelays.length - 1];
    state.restoreRetryCount += 1;
    state.restoreRetryTimer = window.setTimeout(() => {
      state.restoreRetryTimer = null;
      restoreSession();
    }, delay);
  }

  function connectWebSocket() {
    if (!state.inviteCode || !state.playerToken) {
      return;
    }
    if (
      state.ws &&
      [WebSocket.OPEN, WebSocket.CONNECTING].includes(state.ws.readyState)
    ) {
      return;
    }
    clearReconnectTimer();
    state.shouldReconnect = true;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(
      `${protocol}//${window.location.host}/api/games/${state.inviteCode}/ws?token=${encodeURIComponent(state.playerToken)}`,
    );
    state.ws = ws;

    ws.addEventListener("open", () => {
      if (state.ws !== ws) {
        return;
      }
      state.wsReady = true;
      state.error = "";
      render();
    });

    ws.addEventListener("message", (event) => {
      if (state.ws !== ws) {
        return;
      }
      const payload = JSON.parse(event.data);
      if (payload.type === "session_snapshot") {
        applyRealtimeSessionSnapshot(payload);
        return;
      }
      if (payload.type === "private_state") {
        applyRealtimePrivateState(payload);
        return;
      }
      if (payload.type === "action_error") {
        handleActionError(payload.message);
        return;
      }
      if (payload.type === "shoutout") {
        appendShoutoutBubble({
          eventId: payload.data?.event_id || "",
          seat: payload.data?.seat,
          preset: payload.data?.preset,
        });
      }
    });

    ws.addEventListener("close", (event) => {
      if (state.ws !== ws) {
        return;
      }
      state.ws = null;
      state.wsReady = false;
      if (event.code === 1008) {
        clearSession(restoreUnavailableMessage);
        return;
      }
      render();
      scheduleReconnect();
    });
  }

  function applyActionSnapshot(snapshotPayload, { detectAnimations = false } = {}) {
    const { previousSnapshot } = applySessionSnapshot(snapshotPayload);
    if (detectAnimations) {
      detectAnimationEvents(previousSnapshot, snapshotPayload.data);
    }
    state.error = "";
  }

  async function createGame(form) {
    const payload = {
      display_name: form.get("display_name"),
    };
    const response = await api("/api/games", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.displayName = payload.display_name.trim();
    applyAuthPayload(response);
  }

  async function joinGame(form) {
    const inviteCode = form.get("invite_code").trim().toUpperCase();
    const payload = {
      display_name: form.get("display_name"),
    };
    const response = await api(`/api/games/${inviteCode}/join`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.displayName = payload.display_name.trim();
    applyAuthPayload(response);
  }

  async function restoreSession({ resetRetry = false } = {}) {
    if (!hasSavedSession() || state.restoringSession) {
      return;
    }
    if (resetRetry) {
      clearRestoreRetryTimer();
      state.restoreRetryCount = 0;
    }
    state.restoringSession = true;
    state.error = "";
    render();
    try {
      const response = await api(`/api/games/${state.inviteCode}/restore`, {
        method: "POST",
        body: JSON.stringify({ player_token: state.playerToken }),
      });
      applyAuthPayload(response);
    } catch (error) {
      state.restoringSession = false;
      if (isPermanentRestoreError(error)) {
        clearSession(restoreUnavailableMessage);
        return;
      }
      state.error = "Could not restore your saved session right now. Try again.";
      render();
      scheduleRestoreRetry();
    }
  }

  function attemptSessionRecovery({ resetRetry = false } = {}) {
    if (!hasSavedSession()) {
      return;
    }
    if (state.snapshot) {
      if (
        !state.ws ||
        ![WebSocket.OPEN, WebSocket.CONNECTING].includes(state.ws.readyState)
      ) {
        connectWebSocket();
      }
      return;
    }
    restoreSession({ resetRetry });
  }

  async function startGame() {
    try {
      const response = await api(`/api/games/${state.inviteCode}/start`, {
        method: "POST",
        body: JSON.stringify({ player_token: state.playerToken }),
      });
      applyActionSnapshot(response, { detectAnimations: true });
      syncTurnNotice(response.data);
      render();
    } catch (error) {
      applyServerError(error.message);
      render();
    }
  }

  async function rematchGame() {
    try {
      const response = await api(`/api/games/${state.inviteCode}/rematch`, {
        method: "POST",
        body: JSON.stringify({
          player_token: state.playerToken,
        }),
      });
      clearGameStateForLobby();
      applyActionSnapshot(response);
      syncTurnNotice(response.data, { suppress: true });
      render();
    } catch (error) {
      applyServerError(error.message);
      render();
    }
  }

  async function updateGameSettings(allowOptionalTakePile) {
    try {
      const response = await api(`/api/games/${state.inviteCode}/settings`, {
        method: "POST",
        body: JSON.stringify({
          player_token: state.playerToken,
          allow_optional_take_pile: allowOptionalTakePile,
        }),
      });
      applyActionSnapshot(response);
      render();
    } catch (error) {
      applyServerError(error.message);
      render();
    }
  }

  async function kickPlayer(seat) {
    try {
      const response = await api(`/api/games/${state.inviteCode}/players/${seat}/kick`, {
        method: "POST",
        body: JSON.stringify({ player_token: state.playerToken }),
      });
      resetKickSeatConfirmation();
      applyActionSnapshot(response);
      syncTurnNotice(response.data);
      render();
    } catch (error) {
      applyServerError(error.message);
      resetKickSeatConfirmation();
      render();
    }
  }

  function sendAction(payload) {
    if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
      state.error = "Realtime connection is not ready.";
      render();
      return false;
    }
    state.ws.send(JSON.stringify(payload));
    return true;
  }

  function sendPlayPrivateCards(
    payload,
    {
      stageOptimistic = false,
      throwCards = [],
      capturedCards = [],
      delayMs = 140,
    } = {},
  ) {
    if (!stageOptimistic) {
      const sent = sendAction(payload);
      resetSelection();
      return sent;
    }

    state.pendingLocalPlay = {
      throwCards: throwCards.map((motion) => ({
        card: motion.card,
        fromRect: motion.toRect,
        delay: motion.delay,
        rotate: motion.rotate,
      })),
      expectedDrawCount: 0,
      actionSent: false,
    };
    state.hiddenLocalHandCardIds = capturedCards.map((entry) => cardId(entry.card));
    throwCards.forEach((motion) => queueLocalMotion(motion));
    resetSelection();
    render();
    state.localPlaySendTimer = window.setTimeout(() => {
      state.localPlaySendTimer = null;
      const sent = sendAction(payload);
      if (!sent) {
        clearPendingLocalPlay();
        render();
        return;
      }
      if (state.pendingLocalPlay) {
        state.pendingLocalPlay.actionSent = true;
      }
    }, delayMs);
    return true;
  }

  function primeLocalShoutoutCooldown() {
    const nextAvailableAt = new Date(Date.now() + shoutoutCooldownMs).toISOString();
    if (state.privateState?.data) {
      state.privateState = {
        ...state.privateState,
        data: {
          ...state.privateState.data,
          shoutout_next_available_at: nextAvailableAt,
        },
      };
      return;
    }
    state.privateState = {
      type: "private_state",
      data: {
        seat: Number.isInteger(state.seat) ? state.seat : 0,
        private_cards: [],
        shoutout_next_available_at: nextAvailableAt,
      },
    };
  }

  return {
    attemptSessionRecovery,
    closeWebSocket,
    createGame,
    joinGame,
    kickPlayer,
    primeLocalShoutoutCooldown,
    rematchGame,
    restoreSession,
    sendAction,
    sendPlayPrivateCards,
    startGame,
    updateGameSettings,
  };
}
