import {
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

function isPermanentRestoreError(error) {
  return (
    ["auth", "not_found"].includes(error.kind) ||
    [400, 401, 403, 404].includes(error.status)
  );
}

export function createSessionController({
  render,
  clearMotionState,
  clearSession,
  appendShoutoutBubble,
  gameUiController,
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
    gameUiController.onAuthPayloadApplied(payload.snapshot);
    persistSession();
    render();
    connectWebSocket();
  }

  function applyRealtimeSessionSnapshot(payload) {
    const { previousSnapshot, snapshot } = applySessionSnapshot(payload, {
      touchPresence: true,
    });
    if (!snapshot?.players?.some((player) => player.seat === state.seat)) {
      clearSession(restoreUnavailableMessage);
      return;
    }
    gameUiController.onRealtimeSessionSnapshotApplied(previousSnapshot, snapshot);
    render();
  }

  function applyRealtimePrivateState(payload) {
    const {
      previousPrivateState,
      previousPrivateCards,
      privateState,
    } = applyPrivateState(payload);
    const outcome = gameUiController.onRealtimePrivateStateApplied({
      previousPrivateState,
      previousPrivateCards,
      privateState,
    });
    if (outcome?.skipRender) {
      return;
    }
    render();
  }

  function handleActionError(message) {
    applyServerError(message);
    gameUiController.onActionError();
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
    gameUiController.onActionSnapshotApplied(previousSnapshot, snapshotPayload.data, {
      detectAnimations,
    });
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
      gameUiController.syncTurnNotice(response.data);
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
      gameUiController.clearGameStateForLobby();
      applyActionSnapshot(response);
      gameUiController.syncTurnNotice(response.data, { suppress: true });
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
      gameUiController.resetKickSeatConfirmation();
      applyActionSnapshot(response);
      gameUiController.syncTurnNotice(response.data);
      render();
    } catch (error) {
      applyServerError(error.message);
      gameUiController.resetKickSeatConfirmation();
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

  return {
    attemptSessionRecovery,
    closeWebSocket,
    createGame,
    joinGame,
    kickPlayer,
    rematchGame,
    restoreSession,
    sendAction,
    startGame,
    updateGameSettings,
  };
}
