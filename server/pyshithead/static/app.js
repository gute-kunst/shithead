const storageKey = "shithead.alpha.session";
const playPilePreviewLimit = 6;
const jokerRank = 15;
const jokerAllowedRanks = [3, 4, 6, 7, 8, 9, 11, 13, 12, 14];
const jokerSymbol = "★";

const state = {
  inviteCode: "",
  playerToken: "",
  seat: null,
  displayName: "",
  snapshot: null,
  privateState: null,
  error: "",
  ws: null,
  wsReady: false,
  reconnectTimer: null,
  restoringSession: false,
  shouldReconnect: false,
  selectedCards: [],
  highLowChoice: "",
  turnNoticeVisible: false,
  turnNoticeHeadline: "",
  turnNoticeCopy: "",
  lastTurnNoticeKey: "",
  turnNoticeTimer: null,
  suppressCardTapUntil: 0,
  landingInviteCode: "",
  landingOpenBucket: "",
  landingJoinFirst: false,
  pendingLandingNameFocus: false,
  restoreRetryTimer: null,
  restoreRetryCount: 0,
  jokerRank: null,
  leaveArmed: false,
  leaveConfirmTimer: null,
  rulesMenuOpen: false,
};

const app = document.getElementById("app");

function loadStoredSession() {
  try {
    const raw = localStorage.getItem(storageKey);
    if (!raw) {
      return;
    }
    const parsed = JSON.parse(raw);
    state.inviteCode = parsed.inviteCode || "";
    state.playerToken = parsed.playerToken || "";
    state.seat = Number.isInteger(parsed.seat) ? parsed.seat : null;
    state.displayName = parsed.displayName || "";
  } catch (error) {
    localStorage.removeItem(storageKey);
  }
}

function persistSession() {
  if (!state.inviteCode || !state.playerToken) {
    localStorage.removeItem(storageKey);
    return;
  }
  localStorage.setItem(
    storageKey,
    JSON.stringify({
      inviteCode: state.inviteCode,
      playerToken: state.playerToken,
      seat: state.seat,
      displayName: state.displayName,
    }),
  );
}

function hasSavedSession() {
  return Boolean(state.inviteCode && state.playerToken);
}

function loadInviteLink() {
  const params = new URLSearchParams(window.location.search);
  const inviteCode = (params.get("invite") || "").trim().toUpperCase();
  if (!inviteCode) {
    return;
  }
  state.landingInviteCode = inviteCode;
  state.landingOpenBucket = "join";
  state.landingJoinFirst = true;
  state.pendingLandingNameFocus = true;
}

function toggleLandingBucket(bucket) {
  const nextBucket = state.landingOpenBucket === bucket ? "" : bucket;
  state.landingOpenBucket = nextBucket;
  if (nextBucket === "join" && state.landingInviteCode) {
    state.pendingLandingNameFocus = true;
  }
  render();
}

function clearReconnectTimer() {
  if (state.reconnectTimer !== null) {
    window.clearTimeout(state.reconnectTimer);
    state.reconnectTimer = null;
  }
}

function clearLeaveConfirmTimer() {
  if (state.leaveConfirmTimer !== null) {
    window.clearTimeout(state.leaveConfirmTimer);
    state.leaveConfirmTimer = null;
  }
}

function resetLeaveConfirmation({ rerender = false } = {}) {
  clearLeaveConfirmTimer();
  state.leaveArmed = false;
  if (rerender) {
    render();
  }
}

function armLeaveConfirmation() {
  clearLeaveConfirmTimer();
  state.leaveArmed = true;
  state.leaveConfirmTimer = window.setTimeout(() => {
    state.leaveConfirmTimer = null;
    state.leaveArmed = false;
    render();
  }, 3000);
}

function handleLeaveClick() {
  if (state.leaveArmed) {
    resetLeaveConfirmation();
    clearSession();
    return;
  }
  armLeaveConfirmation();
  render();
}

function openRulesMenu() {
  state.rulesMenuOpen = true;
  render();
}

function closeRulesMenu() {
  if (!state.rulesMenuOpen) {
    return;
  }
  state.rulesMenuOpen = false;
  render();
}

function clearTurnNoticeTimer() {
  if (state.turnNoticeTimer !== null) {
    window.clearTimeout(state.turnNoticeTimer);
    state.turnNoticeTimer = null;
  }
}

function clearRestoreRetryTimer() {
  if (state.restoreRetryTimer !== null) {
    window.clearTimeout(state.restoreRetryTimer);
    state.restoreRetryTimer = null;
  }
}

function hideTurnNotice() {
  clearTurnNoticeTimer();
  state.turnNoticeVisible = false;
}

function showTurnNotice(headline, copy) {
  clearTurnNoticeTimer();
  state.turnNoticeHeadline = headline;
  state.turnNoticeCopy = copy;
  state.turnNoticeVisible = true;
  state.turnNoticeTimer = window.setTimeout(() => {
    state.turnNoticeTimer = null;
    state.turnNoticeVisible = false;
    render();
  }, 2600);
}

function closeWebSocket({ allowReconnect = false } = {}) {
  clearReconnectTimer();
  state.shouldReconnect = allowReconnect;
  state.wsReady = false;
  const websocket = state.ws;
  state.ws = null;
  if (websocket && [WebSocket.OPEN, WebSocket.CONNECTING].includes(websocket.readyState)) {
    websocket.close();
  }
}

function clearSession(errorMessage = "") {
  closeWebSocket();
  hideTurnNotice();
  clearRestoreRetryTimer();
  resetLeaveConfirmation();
  state.rulesMenuOpen = false;
  state.inviteCode = "";
  state.playerToken = "";
  state.seat = null;
  state.displayName = "";
  state.snapshot = null;
  state.privateState = null;
  state.error = errorMessage;
  state.restoringSession = false;
  state.selectedCards = [];
  state.highLowChoice = "";
  state.lastTurnNoticeKey = "";
  state.restoreRetryCount = 0;
  persistSession();
  render();
}

function forgetSavedSession() {
  closeWebSocket();
  hideTurnNotice();
  clearRestoreRetryTimer();
  resetLeaveConfirmation();
  state.rulesMenuOpen = false;
  state.inviteCode = "";
  state.playerToken = "";
  state.seat = null;
  state.displayName = "";
  state.snapshot = null;
  state.privateState = null;
  state.error = "";
  state.restoringSession = false;
  state.selectedCards = [];
  state.highLowChoice = "";
  state.lastTurnNoticeKey = "";
  state.restoreRetryCount = 0;
  persistSession();
  render();
}

function cardId(card) {
  return `${card.rank}-${card.suit}`;
}

function isJokerCard(card) {
  return Boolean(card && (card.is_joker || card.rank === jokerRank));
}

function cardEffectiveRank(card) {
  if (!card) {
    return null;
  }
  return isJokerCard(card) && Number.isInteger(card.effective_rank) ? card.effective_rank : card.rank;
}

function rankLabel(rank) {
  const map = {
    2: "2",
    3: "3",
    4: "4",
    5: "5",
    6: "6",
    7: "7",
    8: "8",
    9: "9",
    10: "10",
    11: "J",
    12: "Q",
    13: "K",
    14: "A",
    15: jokerSymbol,
  };
  return map[rank] || String(rank);
}

function suitLabel(suit) {
  const map = {
    1: "&diams;",
    2: "&hearts;",
    3: "&clubs;",
    4: "&spades;",
    5: "&#9733;",
    6: "&#9734;",
  };
  return map[suit] || "?";
}

function isRedSuit(suit) {
  return suit === 1 || suit === 2 || suit === 5;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function ordinal(value) {
  const mod100 = value % 100;
  if (mod100 >= 11 && mod100 <= 13) {
    return `${value}th`;
  }
  const mod10 = value % 10;
  if (mod10 === 1) {
    return `${value}st`;
  }
  if (mod10 === 2) {
    return `${value}nd`;
  }
  if (mod10 === 3) {
    return `${value}rd`;
  }
  return `${value}th`;
}

function me() {
  return state.snapshot?.data?.players.find((player) => player.seat === state.seat) || null;
}

function winner() {
  return state.snapshot?.data?.players.find((player) => player.finished_position === 1) || null;
}

function turnPlayer() {
  return (
    state.snapshot?.data?.players.find(
      (player) => player.seat === state.snapshot?.data?.current_turn_seat,
    ) || null
  );
}

function currentGameState() {
  return state.snapshot?.data?.game_state || null;
}

function isMyTurn() {
  return state.snapshot?.data?.current_turn_seat === state.seat;
}

function canChoosePublicCards() {
  const self = me();
  return (
    currentGameState() === "PLAYERS_CHOOSE_PUBLIC_CARDS" &&
    self &&
    self.public_cards.length === 0 &&
    (state.privateState?.data?.private_cards.length || 0) >= 3
  );
}

function canPlayHiddenCard() {
  const self = me();
  return (
    currentGameState() === "DURING_GAME" &&
    isMyTurn() &&
    self &&
    self.public_cards.length === 0 &&
    self.hidden_cards_count > 0 &&
    (state.privateState?.data?.private_cards.length || 0) === 0
  );
}

function hasPlayablePrivateCard(snapshot = state.snapshot?.data) {
  if (currentGameState() !== "DURING_GAME" || !isMyTurn()) {
    return false;
  }

  const validRanks = new Set(snapshot?.current_valid_ranks || []);
  return privateCards().some((card) => {
    if (isJokerCard(card)) {
      return jokerAllowedRanks.some((rank) => validRanks.has(rank));
    }
    return validRanks.has(card.rank);
  });
}

function mustTakePile(snapshot = state.snapshot?.data) {
  return (
    currentGameState() === "DURING_GAME"
    && isMyTurn()
    && privateCards().length > 0
    && !canPlayHiddenCard()
    && !hasPlayablePrivateCard(snapshot)
  );
}

function privateCards() {
  return state.privateState?.data?.private_cards || [];
}

function selectedRank() {
  if (state.selectedCards.length === 0) {
    return null;
  }
  const nonJokerRank = selectedNonJokerRank();
  if (nonJokerRank !== null) {
    return nonJokerRank;
  }
  return state.jokerRank;
}

function resetSelection() {
  state.selectedCards = [];
  state.highLowChoice = "";
  state.jokerRank = null;
}

function selectedHasJoker() {
  return state.selectedCards.some((card) => isJokerCard(card));
}

function selectedNonJokerRank() {
  const ranks = [...new Set(state.selectedCards.filter((card) => !isJokerCard(card)).map((card) => card.rank))];
  if (ranks.length !== 1) {
    return null;
  }
  return ranks[0];
}

function pendingJokerCard() {
  return state.privateState?.data?.pending_joker_card || null;
}

function hasPendingJokerSelection() {
  return Boolean(state.privateState?.data?.pending_joker_selection && pendingJokerCard());
}

function jokerOptions(snapshot = state.snapshot?.data, cards = state.selectedCards) {
  if (!cards.some((card) => isJokerCard(card))) {
    return [];
  }
  const validRanks = new Set(snapshot?.current_valid_ranks || []);
  const nonJokerRanks = [...new Set(cards.filter((card) => !isJokerCard(card)).map((card) => card.rank))];
  if (nonJokerRanks.length > 1) {
    return [];
  }
  if (nonJokerRanks.length === 1) {
    const [rank] = nonJokerRanks;
    return jokerAllowedRanks.includes(rank) && validRanks.has(rank) ? [rank] : [];
  }
  return jokerAllowedRanks.filter((rank) => validRanks.has(rank));
}

function syncJokerSelection() {
  if (state.selectedCards.length === 0) {
    state.jokerRank = null;
    state.highLowChoice = "";
    return;
  }

  if (canChoosePublicCards()) {
    state.jokerRank = null;
    state.highLowChoice = "";
    return;
  }

  if (selectedHasJoker()) {
    const nonJokerRank = selectedNonJokerRank();
    if (nonJokerRank !== null) {
      state.jokerRank = nonJokerRank;
    } else if (!jokerOptions().includes(state.jokerRank)) {
      state.jokerRank = null;
    }
  } else {
    state.jokerRank = null;
  }

  if (selectedRank() !== state.snapshot?.data?.rules.high_low_rank) {
    state.highLowChoice = "";
  }
}

function playRank() {
  return selectedHasJoker() ? state.jokerRank : selectedRank();
}

function buildInviteLink() {
  const inviteUrl = new URL("/", window.location.origin);
  inviteUrl.searchParams.set("invite", state.inviteCode);
  return inviteUrl.toString();
}

function turnNoticePayload(snapshot) {
  let headline = "Waiting";
  if (snapshot.status === "GAME_OVER") {
    headline = `${winner()?.display_name || "A player"} won`;
  } else if (snapshot.status === "LOBBY") {
    headline = "Lobby";
  } else if (isMyTurn()) {
    headline = currentGameState() === "PLAYERS_CHOOSE_PUBLIC_CARDS" ? "Choose your cards" : "It's your turn!";
  } else if (snapshot.current_turn_display_name) {
    headline = `${snapshot.current_turn_display_name} is up`;
  }

  return {
    key: [
      snapshot.status,
      snapshot.game_state || "",
      snapshot.current_turn_seat ?? "none",
      state.seat ?? "none",
    ].join(":"),
    headline,
    copy: currentPrompt({ type: "session_snapshot", data: snapshot }),
  };
}

function syncTurnNotice(snapshot, { suppress = false } = {}) {
  if (!snapshot) {
    hideTurnNotice();
    state.lastTurnNoticeKey = "";
    return;
  }

  const notice = turnNoticePayload(snapshot);
  const hasChanged = notice.key !== state.lastTurnNoticeKey;
  state.lastTurnNoticeKey = notice.key;

  if (suppress || !isMobileActiveGameLayout(snapshot)) {
    state.turnNoticeVisible = false;
    return;
  }

  if (hasChanged) {
    showTurnNotice(notice.headline, notice.copy);
  }
}

function toggleCard(card) {
  const exists = state.selectedCards.some((selected) => cardId(selected) === cardId(card));
  if (exists) {
    state.selectedCards = state.selectedCards.filter((selected) => cardId(selected) !== cardId(card));
    syncJokerSelection();
    render();
    return;
  }

  if (canChoosePublicCards()) {
    if (state.selectedCards.length >= 3) {
      state.error = "Choose exactly 3 cards.";
      render();
      return;
    }
    state.selectedCards = [...state.selectedCards, card];
    state.error = "";
    render();
    return;
  }

  if (currentGameState() === "DURING_GAME") {
    const nonJokerRank = selectedNonJokerRank();
    if (isJokerCard(card)) {
      if (nonJokerRank !== null && !jokerAllowedRanks.includes(nonJokerRank)) {
        state.error = "Jokers cannot be 2, 5, or 10.";
        render();
        return;
      }
      state.selectedCards = [...state.selectedCards, card];
      state.error = "";
      syncJokerSelection();
    } else if (selectedHasJoker() && nonJokerRank === null && state.selectedCards.length > 0) {
      if (!jokerAllowedRanks.includes(card.rank)) {
        state.error = "Jokers cannot be 2, 5, or 10.";
        render();
        return;
      }
      state.selectedCards = [...state.selectedCards, card];
      state.error = "";
      syncJokerSelection();
    } else if (state.selectedCards.length === 0 || nonJokerRank === card.rank) {
      if (selectedHasJoker() && !jokerAllowedRanks.includes(card.rank)) {
        state.error = "Jokers cannot be 2, 5, or 10.";
        render();
        return;
      }
      state.selectedCards = [...state.selectedCards, card];
      state.error = "";
      syncJokerSelection();
    } else {
      state.error = "You can only select cards of the same rank.";
    }
    render();
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
  state.inviteCode = payload.invite_code;
  state.playerToken = payload.player_token;
  state.seat = payload.seat;
  state.snapshot = { type: "session_snapshot", data: payload.snapshot };
  state.privateState = { type: "private_state", data: payload.private_state };
  state.displayName = payload.snapshot.players.find((player) => player.seat === payload.seat)?.display_name
    || state.displayName;
  state.error = "";
  state.restoringSession = false;
  resetSelection();
  clearRestoreRetryTimer();
  state.restoreRetryCount = 0;
  persistSession();
  syncTurnNotice(payload.snapshot, { suppress: true });
  render();
  connectWebSocket();
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

function isPermanentRestoreError(error) {
  return ["auth", "not_found"].includes(error.kind) || [400, 401, 403, 404].includes(error.status);
}

function scheduleRestoreRetry() {
  if (!hasSavedSession() || state.snapshot || state.restoringSession || state.restoreRetryCount >= 3) {
    return;
  }
  clearRestoreRetryTimer();
  const retryDelays = [1500, 4000, 8000];
  const delay = retryDelays[state.restoreRetryCount] || retryDelays[retryDelays.length - 1];
  state.restoreRetryCount += 1;
  state.restoreRetryTimer = window.setTimeout(() => {
    state.restoreRetryTimer = null;
    restoreSession();
  }, delay);
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
      clearSession("Your saved session is no longer available. Join the game again if it is still active.");
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
    if (!state.ws || ![WebSocket.OPEN, WebSocket.CONNECTING].includes(state.ws.readyState)) {
      connectWebSocket();
    }
    return;
  }
  restoreSession({ resetRetry });
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

function connectWebSocket() {
  if (!state.inviteCode || !state.playerToken) {
    return;
  }
  if (state.ws && [WebSocket.OPEN, WebSocket.CONNECTING].includes(state.ws.readyState)) {
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
      state.snapshot = payload;
      if (!payload.data.players.some((player) => player.seat === state.seat)) {
        clearSession("Your saved session is no longer available. Join the game again if it is still active.");
        return;
      }
      syncTurnNotice(payload.data);
      if (payload.data.status === "GAME_OVER" || !isMyTurn()) {
        resetSelection();
      }
      render();
    } else if (payload.type === "private_state") {
      state.privateState = payload;
      if (payload.data.pending_joker_selection) {
        state.selectedCards = [];
        state.jokerRank = payload.data.pending_joker_card?.effective_rank || null;
        state.highLowChoice = "";
      }
      render();
    } else if (payload.type === "action_error") {
      state.error = payload.message;
      render();
    }
  });

  ws.addEventListener("close", (event) => {
    if (state.ws !== ws) {
      return;
    }
    state.ws = null;
    state.wsReady = false;
    if (event.code === 1008) {
      clearSession("Your saved session is no longer available. Join the game again if it is still active.");
      return;
    }
    render();
    scheduleReconnect();
  });
}

async function startGame() {
  try {
    const response = await api(`/api/games/${state.inviteCode}/start`, {
      method: "POST",
      body: JSON.stringify({ player_token: state.playerToken }),
    });
    state.snapshot = response;
    state.error = "";
    syncTurnNotice(response.data);
    render();
  } catch (error) {
    state.error = error.message;
    render();
  }
}

function sendAction(payload) {
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
    state.error = "Realtime connection is not ready.";
    render();
    return;
  }
  state.ws.send(JSON.stringify(payload));
}

function submitChoosePublicCards() {
  if (state.selectedCards.length !== 3) {
    state.error = "Choose exactly 3 cards.";
    render();
    return;
  }
  sendAction({
    type: "choose_public_cards",
    cards: state.selectedCards,
  });
  resetSelection();
}

function submitPlayCards() {
  if (state.selectedCards.length === 0) {
    state.error = "Select at least one card.";
    render();
    return;
  }
  if (selectedHasJoker() && !state.jokerRank) {
    state.error = "Choose what the joker should be first.";
    render();
    return;
  }
  if (
    playRank() === state.snapshot.data.rules.high_low_rank &&
    !["HIGHER", "LOWER"].includes(state.highLowChoice)
  ) {
    state.error = "Choose whether the next player must go higher or may go lower.";
    render();
    return;
  }
  sendAction({
    type: "play_private_cards",
    cards: state.selectedCards,
    choice: playRank() === state.snapshot.data.rules.high_low_rank ? state.highLowChoice : "",
    joker_rank: selectedHasJoker() ? state.jokerRank : null,
  });
  resetSelection();
}

function submitTakePile() {
  sendAction({ type: "take_play_pile" });
}

function submitHiddenCard() {
  sendAction({ type: "play_hidden_card" });
}

function submitResolveJoker() {
  if (!hasPendingJokerSelection()) {
    state.error = "No joker is waiting to be resolved.";
    render();
    return;
  }
  if (!state.jokerRank) {
    state.error = "Choose what the joker should be first.";
    render();
    return;
  }
  if (
    state.jokerRank === state.snapshot.data.rules.high_low_rank &&
    !["HIGHER", "LOWER"].includes(state.highLowChoice)
  ) {
    state.error = "Choose whether the next player must go higher or may go lower.";
    render();
    return;
  }
  sendAction({
    type: "resolve_joker",
    choice: state.jokerRank === state.snapshot.data.rules.high_low_rank ? state.highLowChoice : "",
    joker_rank: state.jokerRank,
  });
  resetSelection();
}

function onSubmit(event) {
  event.preventDefault();
  state.error = "";
  const form = new FormData(event.currentTarget);
  const mode = event.currentTarget.dataset.mode;
  if (mode === "create") {
    createGame(form).catch((error) => {
      state.error = error.message;
      render();
    });
  } else if (mode === "join") {
    joinGame(form).catch((error) => {
      state.error = error.message;
      render();
    });
  }
}

function renderCard(card, selected, clickable = true) {
  const classes = ["card"];
  if (selected) {
    classes.push("selected");
  }
  if (isJokerCard(card)) {
    classes.push("joker");
  }
  if (isRedSuit(card.suit)) {
    classes.push("red");
  }
  const disabled = clickable ? "" : "disabled";
  const rankMarkup = isJokerCard(card) ? jokerSymbol : rankLabel(card.rank);
  const detailMarkup = isJokerCard(card)
    ? `<span class="card-joker-tag">${card.effective_rank ? `as ${rankLabel(card.effective_rank)}` : "wild"}</span>`
    : `<span class="card-suit">${suitLabel(card.suit)}</span>`;
  return `
    <button class="${classes.join(" ")}" data-card-id="${cardId(card)}" ${disabled}>
      <span class="card-rank">${rankMarkup}</span>
      ${detailMarkup}
    </button>
  `;
}

function relativeSeatIndex(snapshot, player) {
  if (state.seat === null || snapshot.players.length === 0) {
    return player.seat;
  }
  return (player.seat - state.seat + snapshot.players.length) % snapshot.players.length;
}

function seatPositionClass(snapshot, player) {
  const relativeIndex = relativeSeatIndex(snapshot, player);
  const layouts = {
    1: ["seat-bottom"],
    2: ["seat-bottom", "seat-top"],
    3: ["seat-bottom", "seat-top-left", "seat-top-right"],
    4: ["seat-bottom", "seat-top-left", "seat-top", "seat-top-right"],
  };
  return layouts[snapshot.players.length]?.[relativeIndex] || "seat-top";
}

function renderSeatBackCard(rotation = 0, offset = 0) {
  return `
    <span
      class="seat-back-card"
      style="transform: translateX(${offset}px) rotate(${rotation}deg);"
      aria-hidden="true"
    ></span>
  `;
}

function renderSeatHandFan(privateCardsCount) {
  if (privateCardsCount <= 0) {
    return '<span class="seat-muted">No hand cards</span>';
  }

  const visibleCards = Math.min(privateCardsCount, 8);
  const rotations = [-18, -13, -9, -4, 1, 6, 11, 16];

  return `
    <div class="seat-hand-fan-wrap" style="--seat-fan-count: ${visibleCards};">
      <div class="seat-hand-fan" aria-hidden="true">
        ${Array.from({ length: visibleCards }, (_, index) => renderSeatBackCard(rotations[index] || 0, index * 4)).join("")}
      </div>
      <span class="seat-count-badge">${privateCardsCount}</span>
    </div>
  `;
}

function renderSeatMiniCard(card) {
  const isJoker = isJokerCard(card);
  return `
    <span class="seat-mini-card ${isRedSuit(card.suit) ? "red" : ""} ${isJoker ? "joker" : ""}">
      <span class="seat-mini-rank">${isJoker ? jokerSymbol : rankLabel(card.rank)}</span>
      <span class="seat-mini-suit">${isJoker ? (card.effective_rank ? rankLabel(card.effective_rank) : "?" ) : suitLabel(card.suit)}</span>
    </span>
  `;
}

function renderSeatPublicStack(publicCards, hiddenCardsCount) {
  if (publicCards.length === 0) {
    return hiddenCardsCount > 0 ? renderSeatHiddenStack(hiddenCardsCount) : '<span class="seat-muted">No table cards</span>';
  }

  return `
    <div class="seat-public-stack">
      ${publicCards
    .map(
      (card) => `
          <span class="seat-public-stack-card">
            <span class="seat-hidden-underlay" aria-hidden="true"></span>
            ${renderSeatMiniCard(card)}
          </span>
        `,
    )
    .join("")}
    </div>
  `;
}

function renderSeatHiddenStack(hiddenCardsCount) {
  if (hiddenCardsCount <= 0) {
    return "";
  }

  return `
    <div class="seat-hidden-stack" aria-hidden="true">
      ${Array.from({ length: hiddenCardsCount }, () => '<span class="seat-back-card hidden-row"></span>').join("")}
    </div>
  `;
}

function renderSeat(snapshot, player) {
  const isCurrentTurn = player.seat === snapshot.current_turn_seat;
  const isWinner = player.finished_position === 1;
  const isYou = player.seat === state.seat;
  const seatClasses = [
    "seat-panel",
    seatPositionClass(snapshot, player),
    isCurrentTurn ? "current-turn" : "",
    isWinner ? "winner" : "",
    isYou ? "you" : "",
    !player.is_connected ? "disconnected" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const seatBadges = [
    isYou ? "You" : "",
    player.is_host ? "Host" : "",
    player.has_finished ? ordinal(player.finished_position) : "",
    !player.is_connected ? "Offline" : "",
  ]
    .filter(Boolean)
    .map((badge) => `<span class="seat-badge">${escapeHtml(badge)}</span>`)
    .join("");

  return `
    <div class="${seatClasses}">
      ${seatBadges ? `<div class="seat-badge-rail">${seatBadges}</div>` : ""}
      <div class="seat-header">
        <div class="seat-title-row">
          <strong>${escapeHtml(player.display_name)}</strong>
        </div>
      </div>
      <div class="seat-hand-row">${renderSeatHandFan(player.private_cards_count)}</div>
      <div class="seat-public-cards">${renderSeatPublicStack(player.public_cards, player.hidden_cards_count)}</div>
    </div>
  `;
}

function renderMiniCard(card) {
  return `
    <div class="mini-card ${isRedSuit(card.suit) ? "red" : ""} ${isJokerCard(card) ? "joker" : ""}">
      <span>${isJokerCard(card) ? jokerSymbol : rankLabel(card.rank)}</span>
      <span>${isJokerCard(card) ? (card.effective_rank ? `as ${rankLabel(card.effective_rank)}` : "wild") : suitLabel(card.suit)}</span>
    </div>
  `;
}

function renderPilePreview(playPile) {
  if (playPile.length === 0) {
    return "";
  }
  return playPile
    .slice(0, playPilePreviewLimit)
    .reverse()
    .map((card) => renderMiniCard(card))
    .join("");
}

function renderDeckPreview(cardsInDeck) {
  const visibleCards = Math.min(cardsInDeck, 3);
  return `
    <div class="deck-stack" aria-hidden="true">
      ${Array.from({ length: visibleCards }, (_, index) => `
        <span
          class="deck-back-card"
          style="transform: translate(${index * 4}px, ${index * 3}px) rotate(${index * 3 - 3}deg);"
        ></span>
      `).join("")}
      <span class="deck-count-badge">${cardsInDeck}</span>
    </div>
  `;
}

function playPileCaption(playPile) {
  if (playPile.length === 0) {
    return "";
  }
  if (playPile.length > playPilePreviewLimit) {
    const hiddenCount = playPile.length - playPilePreviewLimit;
    return `+${hiddenCount} card${hiddenCount === 1 ? "" : "s"}`;
  }
  return "";
}

function displayedDeckCount(snapshot) {
  if (snapshot.status === "LOBBY") {
    return 54;
  }
  return snapshot.cards_in_deck;
}

function isMobileActiveGameLayout(snapshot = state.snapshot?.data) {
  return Boolean(snapshot) && snapshot.status !== "GAME_OVER";
}

function isMobileLobbyLayout(snapshot = state.snapshot?.data) {
  return Boolean(snapshot) && snapshot.status === "LOBBY";
}

function tableLayoutVariant(snapshot = state.snapshot?.data) {
  if (!isMobileActiveGameLayout(snapshot)) {
    return "balanced";
  }
  const viewportWidth = window.innerWidth || 390;
  const viewportHeight = Math.max(window.innerHeight || 844, 1);
  const aspectRatio = viewportWidth / viewportHeight;
  if (aspectRatio < 0.52) {
    return "tall";
  }
  if (aspectRatio > 0.68) {
    return "wide";
  }
  return "balanced";
}

function handLayout(snapshot) {
  const cardCount = privateCards().length;
  const playerCount = snapshot.players.length;
  const viewportWidth = window.innerWidth || 390;
  const viewportHeight = window.innerHeight || 844;
  const compactViewport = viewportHeight < 760 || playerCount >= 4 || viewportWidth < 420;
  const narrowViewport = viewportWidth < 400;
  const availableWidth = Math.max(viewportWidth - 64, 220);
  const maxWidth = compactViewport ? 46 : 72;
  const minWidth = compactViewport ? 36 : 46;
  const stepFactor = cardCount >= 7 ? 0.48 : cardCount >= 5 ? 0.54 : 0.62;
  const fitWidth = cardCount <= 1
    ? maxWidth
    : Math.floor(availableWidth / (1 + Math.max(0, cardCount - 1) * stepFactor));
  const shouldScroll = (
    cardCount > 0
    && (
      fitWidth < minWidth
      || (compactViewport && cardCount >= 5)
      || (narrowViewport && cardCount >= 4)
    )
  );
  const cardWidth = shouldScroll
    ? (compactViewport ? (narrowViewport ? 35 : 38) : 56)
    : Math.max(minWidth, Math.min(maxWidth, fitWidth || maxWidth));
  const overlap = Math.round(cardWidth * (shouldScroll ? 0.26 : 1 - stepFactor));
  const cardHeight = Math.round(cardWidth * 1.42);
  const lift = Math.max(6, Math.round(cardHeight * 0.13));
  const classes = [
    shouldScroll ? "hand-layout-scroll" : "hand-layout-fit",
    cardWidth <= 52 ? "hand-layout-compact" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return {
    classes,
    style: [
      `--hand-card-width:${cardWidth}px`,
      `--hand-card-height:${cardHeight}px`,
      `--hand-card-overlap:${overlap}px`,
      `--hand-card-lift:${lift}px`,
    ].join(";"),
  };
}

function currentPrompt(snapshot) {
  const turnTarget = snapshot.current_turn_display_name
    || (Number.isInteger(snapshot.current_turn_seat) ? `Seat ${snapshot.current_turn_seat}` : "the next player");
  if (snapshot.status === "LOBBY") {
    return "Share the code, wait for enough players, then start.";
  }
  if (snapshot.status === "GAME_OVER") {
    return "Final standings are ready below.";
  }
  if (canChoosePublicCards()) {
    return "Pick 3 public cards for the table.";
  }
  if (currentGameState() === "DURING_GAME" && isMyTurn()) {
    if (hasPendingJokerSelection()) {
      return "Choose which rank the revealed joker should be.";
    }
    if (selectedHasJoker() && !state.jokerRank) {
      return "Choose which rank the joker should be before playing.";
    }
    if (playRank() === snapshot.rules.high_low_rank) {
      return "Choose how the 7 changes the next player's turn.";
    }
    if (canPlayHiddenCard()) {
      return "Your hidden cards are live. Take a hidden card.";
    }
    if (mustTakePile(snapshot)) {
      return "No legal card to play. Take the pile.";
    }
    return "Tap matching cards from your hand.";
  }
  if (currentGameState() === "DURING_GAME") {
    return `Waiting for ${turnTarget} to play.`;
  }
  return "Waiting for the game to begin.";
}

function renderLandingTopbar() {
  return `
    <div class="game-topbar">
      <div class="game-topbar-title">
        <strong class="game-topbar-name">Shithead</strong>
        <span class="game-topbar-eyebrow">Private Mobile Alpha</span>
      </div>
    </div>
  `;
}

function renderLandingBucket(bucket) {
  const expanded = state.landingOpenBucket === bucket;
  const isCreate = bucket === "create";
  const title = isCreate ? "Create table" : "Join a table";
  const copy = isCreate
    ? "Start a private lobby and get an invite code for the other players."
    : "Enter the invite code and your display name to claim a seat.";
  const buttonLabel = isCreate ? "Create game" : "Join game";
  const formMarkup = isCreate
    ? `
      <form class="stack" data-mode="create">
        <div class="field">
          <label for="create-name">Display name</label>
          <input id="create-name" name="display_name" maxlength="24" required placeholder="your-name" />
        </div>
        <button class="button accent" type="submit">${buttonLabel}</button>
      </form>
    `
    : `
      <form class="stack" data-mode="join">
        <div class="field">
          <label for="join-code">Invite code</label>
          <input id="join-code" name="invite_code" maxlength="6" required placeholder="AB12CD" value="${escapeHtml(state.landingInviteCode)}" />
        </div>
        <div class="field">
          <label for="join-name">Display name</label>
          <input id="join-name" name="display_name" maxlength="24" required placeholder="your-name" />
        </div>
        <button class="button" type="submit">${buttonLabel}</button>
      </form>
    `;

  return `
    <article class="landing-table-card ${expanded ? "landing-table-card-expanded" : "landing-table-card-collapsed"} stack">
      <button
        class="landing-bucket-toggle"
        type="button"
        data-landing-bucket="${bucket}"
        aria-expanded="${expanded ? "true" : "false"}"
      >
        <span class="landing-bucket-copy">
          <strong>${title}</strong>
        </span>
        <span class="landing-bucket-icon" aria-hidden="true">${expanded ? "-" : "+"}</span>
      </button>
      <div class="landing-bucket-panel" aria-hidden="${expanded ? "false" : "true"}">
        <div class="landing-bucket-panel-inner stack">
          <p class="muted">${copy}</p>
          ${formMarkup}
        </div>
      </div>
    </article>
  `;
}

function renderLanding() {
  const showSavedSessionCard = hasSavedSession();
  const landingBuckets = state.landingJoinFirst
    ? [renderLandingBucket("join"), renderLandingBucket("create")]
    : [renderLandingBucket("create"), renderLandingBucket("join")];
  return `
    ${renderLandingTopbar()}
    <section class="game-screen landing-screen">
      <section class="panel table-stage landing-table-stage">
        <div class="table-map landing-table-map">
          <div class="table-surface"></div>
          <div class="landing-table-content">
            <div class="landing-table-banner-row">
              <section class="landing-table-banner landing-alpha-banner">
                <strong>Alpha notice</strong>
                <p>Keep the tab open while you play. Live games can reset after a deploy, restart, or a long period of inactivity.</p>
              </section>
            </div>
            <div class="landing-form-row">
              ${landingBuckets.join("")}
            </div>
            ${showSavedSessionCard ? `
              <div class="landing-table-banner-row landing-table-banner-row-bottom">
                <section class="landing-table-banner landing-table-resume stack">
                  <div>
                    <strong>${state.restoringSession ? "Restoring your game" : "Resume saved game"}</strong>
                    <p class="muted">
                      ${state.restoringSession
    ? "Reclaiming your seat and reconnecting to live updates."
    : "A saved game was found on this device. You can restore it or forget it."}
                    </p>
                  </div>
                  <div class="status-strip">
                    <span class="status-chip">Invite ${escapeHtml(state.inviteCode)}</span>
                    ${state.displayName ? `<span class="status-chip">${escapeHtml(state.displayName)}</span>` : ""}
                  </div>
                  ${state.error ? `<div class="dock-error">${escapeHtml(state.error)}</div>` : ""}
                  ${!state.restoringSession ? `
                    <div class="secondary-action-row">
                      <button class="button accent" id="restore-session">Restore saved session</button>
                      <button class="button secondary" id="forget-session">Forget saved session</button>
                    </div>
                  ` : ""}
                </section>
              </div>
            ` : state.error ? `
              <div class="landing-table-banner-row landing-table-banner-row-bottom">
                <section class="landing-table-banner landing-table-error">
                  <strong>${escapeHtml(state.error)}</strong>
                </section>
              </div>
            ` : ""}
          </div>
          <button class="table-help-trigger" id="open-rules-menu" type="button" aria-label="Open rules" title="Rules">?</button>
          ${renderRulesMenu()}
        </div>
      </section>
    </section>
  `;
}

function renderStandings(snapshot) {
  const placedPlayers = snapshot.players
    .filter((player) => player.finished_position !== null)
    .sort((left, right) => left.finished_position - right.finished_position);

  if (placedPlayers.length === 0) {
    return "";
  }

  return `
    <section class="panel stack">
      <h2>Standings</h2>
      <div class="standings">
        ${placedPlayers
          .map(
            (player) => `
              <div class="standing-row">
                <strong>${ordinal(player.finished_position)} - ${escapeHtml(player.display_name)}</strong>
                <span>${player.seat === state.seat ? "You" : `Seat ${player.seat}`}</span>
              </div>
            `,
          )
          .join("")}
      </div>
    </section>
  `;
}

function renderActions(snapshot) {
  const cards = privateCards();
  const selectedIds = new Set(state.selectedCards.map((card) => cardId(card)));
  const pendingCard = pendingJokerCard();
  const pendingJoker = hasPendingJokerSelection();
  const allowJokerDefinition = pendingJoker || (
    currentGameState() === "DURING_GAME"
    && isMyTurn()
    && selectedHasJoker()
  );
  const jokerChoices = pendingJoker ? jokerOptions(snapshot, [pendingCard]) : jokerOptions(snapshot);
  const currentPlayRank = pendingJoker ? state.jokerRank : playRank();
  const showHighLowChoice = currentPlayRank === snapshot.rules.high_low_rank;
  const hasHighLowChoice = ["HIGHER", "LOWER"].includes(state.highLowChoice);
  const turnName = snapshot.current_turn_display_name
    || (Number.isInteger(snapshot.current_turn_seat) ? `Seat ${snapshot.current_turn_seat}` : "the next player");
  const layout = handLayout(snapshot);
  const showTakePileOverlay = mustTakePile(snapshot);
  const showHiddenAction = canPlayHiddenCard();
  const showMobileTurnPrompt = isMobileActiveGameLayout(snapshot) && currentGameState() === "DURING_GAME";
  const showPlaySelectedAction = (
    currentGameState() === "DURING_GAME"
    && isMyTurn()
    && !showHiddenAction
    && !showTakePileOverlay
    && !pendingJoker
  );
  const playSelectedDisabled = cards.length === 0
    || (selectedHasJoker() && !state.jokerRank)
    || (showHighLowChoice && !hasHighLowChoice);
  let handPrimaryAction = null;
  if (canChoosePublicCards()) {
    handPrimaryAction = { action: "choose-public", label: "Lock cards", disabled: false };
  } else if (pendingJoker) {
    handPrimaryAction = {
      action: "resolve-joker",
      label: "Play joker",
      disabled: state.jokerRank === null || (showHighLowChoice && !hasHighLowChoice),
    };
  } else if (showHiddenAction) {
    handPrimaryAction = { action: "play-hidden", label: "Take hidden card", disabled: false };
  } else if (showPlaySelectedAction) {
    handPrimaryAction = { action: "play-cards", label: "Play cards", disabled: playSelectedDisabled };
  }
  const dockClasses = [
    "panel",
    "hand-dock",
    layout.classes,
    currentGameState() === "DURING_GAME" && !isMyTurn() ? "waiting" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return `
    <section class="${dockClasses}" style="${layout.style}">
      <div class="dock-header">
        <div class="dock-header-main">
          <p class="section-title">Your hand</p>
        </div>
        ${handPrimaryAction ? `
          <button
            class="button accent button-inline dock-header-action"
            id="hand-primary-action"
            data-hand-action="${handPrimaryAction.action}"
            ${handPrimaryAction.disabled ? "disabled" : ""}
          >${handPrimaryAction.label}</button>
        ` : ""}
      </div>
      <div class="dock-prompt">${escapeHtml(currentPrompt(snapshot))}</div>
      ${state.error ? `<div class="dock-error">${escapeHtml(state.error)}</div>` : ""}
      ${pendingJoker ? `
        <div class="joker-pending-card">
          ${renderCard(pendingCard, false, false)}
        </div>
      ` : `
        <div class="hand-fan">
          ${
            cards.map((card) => renderCard(card, selectedIds.has(cardId(card)))).join("")
              || '<p class="muted">No cards in hand right now.</p>'
          }
        </div>
      `}
      <div class="actions">
        ${allowJokerDefinition ? `
          <div class="choice-block">
            <strong class="choice-title">${pendingJoker ? "Choose the revealed joker" : "Choose the joker rank"}</strong>
            <div class="joker-choice-row">
              ${jokerChoices.map((rank) => `
                <button
                  class="button ${state.jokerRank === rank ? "accent" : "secondary"}"
                  data-joker-rank="${rank}"
                >${rankLabel(rank)}</button>
              `).join("")}
            </div>
          </div>
        ` : ""}
        ${showHighLowChoice ? `
          <div class="choice-block">
            <div class="choice-row">
              <button class="button ${state.highLowChoice === "LOWER" ? "accent" : "secondary"}" id="choose-lower">7 or lower</button>
              <button class="button ${state.highLowChoice === "HIGHER" ? "accent" : "secondary"}" id="choose-higher">7 or higher</button>
            </div>
          </div>
        ` : ""}
        ${currentGameState() === "DURING_GAME" && !isMyTurn() && !showMobileTurnPrompt ? `<p class="muted tiny">Waiting for ${escapeHtml(turnName)}.</p>` : ""}
      </div>
    </section>
  `;
}

function renderGameTopbar(snapshot) {
  if (!snapshot) {
    resetLeaveConfirmation();
    return "";
  }
  const showCompactBrand = isMobileActiveGameLayout(snapshot);
  const leaveButtonLabel = "Leave";
  const leaveButtonTitle = state.leaveArmed ? "Click again to leave" : "Leave";

  return `
    <div class="game-topbar ${showCompactBrand ? "" : "actions-only"}">
      ${showCompactBrand ? `
        <div class="game-topbar-title">
          <strong class="game-topbar-name">Shithead</strong>
          <span class="game-topbar-eyebrow">Private Mobile Alpha</span>
        </div>
      ` : ""}
      <div class="game-topbar-actions">
        <span
          class="connection-indicator ${state.wsReady ? "connected" : "reconnecting"}"
          title="${state.wsReady ? "Live sync connected" : "Reconnecting"}"
          aria-label="${state.wsReady ? "Live sync connected" : "Reconnecting"}"
        ></span>
        <button
          class="button secondary button-inline ${state.leaveArmed ? "armed-leave" : ""}"
          id="leave-game-header"
          title="${leaveButtonTitle}"
          aria-label="${leaveButtonTitle}"
        >${leaveButtonLabel}</button>
      </div>
    </div>
  `;
}

function renderTurnToast(snapshot) {
  if (!isMobileActiveGameLayout(snapshot) || !state.turnNoticeVisible) {
    return "";
  }

  return `
    <div class="turn-toast" aria-live="polite">
      <strong>${escapeHtml(state.turnNoticeHeadline)}</strong>
      <span>${escapeHtml(state.turnNoticeCopy)}</span>
    </div>
  `;
}

function renderPileAction(snapshot) {
  if (!mustTakePile(snapshot)) {
    return "";
  }

  return `
    <button class="button accent pile-action" id="take-pile-overlay">
      Take pile
    </button>
  `;
}

function renderRulesMenu() {
  if (!state.rulesMenuOpen) {
    return "";
  }

  return `
    <div class="rules-menu-layer">
      <button
        class="rules-menu-backdrop"
        id="close-rules-menu-backdrop"
        type="button"
        aria-label="Close rules menu"
      ></button>
      <section class="rules-menu" aria-label="Game rules">
        <div class="rules-menu-header">
          <div>
            <p class="section-title">Rules</p>
            <strong>How to play</strong>
          </div>
          <button class="button secondary button-inline" id="close-rules-menu" type="button">Close</button>
        </div>
        <div class="rules-menu-copy stack">
          <div class="rules-block">
            <strong>Goal</strong>
            <p>Get rid of all your cards first.</p>
          </div>
          <div class="rules-block">
            <strong>Setup</strong>
            <p>Choose 3 public cards first. Your hand is played before public cards, and hidden cards come last.</p>
          </div>
          <div class="rules-block">
            <strong>Turn flow</strong>
            <p>Play one or more cards of the same rank. If you cannot play, you take the whole play pile. Once your hand is empty, you use public cards, then hidden cards.</p>
          </div>
          <div class="rules-block">
            <strong>Special cards</strong>
            <p>2 resets the pile. 5 is invisible. 7 forces the next play to be higher or lower. 8 skips. 10 burns. Jokers can be any rank except 2, 5, and 10.</p>
          </div>
          <div class="rules-block">
            <strong>Feminist deck</strong>
            <p>Queen outranks the King.</p>
          </div>
          <div class="rules-block">
            <strong>Burn rule</strong>
            <p>Four cards of the same rank burn the pile, and yes, a sneaky invisible 5 can interrupt them and it still totally counts.</p>
          </div>
        </div>
      </section>
    </div>
  `;
}

function renderTable(snapshot) {
  const self = me();
  const isHost = self && self.is_host;
  const showLobbyControls = snapshot.status === "LOBBY";
  const showMobileLobbyLayout = isMobileLobbyLayout(snapshot);
  const sortedPlayers = [...snapshot.players].sort(
    (left, right) => relativeSeatIndex(snapshot, left) - relativeSeatIndex(snapshot, right),
  );

  const lobbyControls = showLobbyControls ? `
    <button
      class="invite-code"
      id="copy-invite-code"
      type="button"
      title="Copy invite code"
      aria-label="Copy invite code"
    >
      <span>Invite code ${snapshot.invite_code}</span>
      <img
        class="invite-code-icon"
        src="/static/icons/content_copy_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
        alt=""
        aria-hidden="true"
      />
    </button>
    <button class="button secondary" id="share-invite">Share invite</button>
  ` : "";

  return `
    <section class="panel table-stage stack">
      ${showMobileLobbyLayout && state.error ? `<div class="dock-error">${escapeHtml(state.error)}</div>` : ""}
      <div class="table-map">
        ${showMobileLobbyLayout ? `
          <div class="table-map-controls">
            ${lobbyControls}
          </div>
        ` : ""}
        <div class="table-surface"></div>
        ${sortedPlayers.map((player) => renderSeat(snapshot, player)).join("")}
        ${renderTurnToast(snapshot)}
        <div class="table-center">
          ${snapshot.status === "LOBBY" && !isHost ? `
            <div class="event-box">
              <span>Waiting for host to start the game.</span>
            </div>
          ` : ""}
          ${snapshot.status_message ? `
            <div class="event-box">
              <span>${escapeHtml(snapshot.status_message)}</span>
            </div>
          ` : ""}
          <div class="table-resources">
            <div class="deck-orb">
              <span class="resource-label">Deck</span>
              ${renderDeckPreview(displayedDeckCount(snapshot))}
            </div>
            <div class="pile-zone">
              <span class="resource-label">Play pile</span>
              <div class="pile-preview">${renderPilePreview(snapshot.play_pile)}</div>
              <span class="pile-caption">${playPileCaption(snapshot.play_pile)}</span>
              ${renderPileAction(snapshot)}
            </div>
          </div>
        </div>
        <button class="table-help-trigger" id="open-rules-menu" type="button" aria-label="Open rules" title="Rules">?</button>
        ${renderRulesMenu()}
      </div>
      ${snapshot.status === "LOBBY" && isHost ? `
        <div class="primary-action-row">
          <button class="button accent full-width" id="start-game" ${snapshot.players.length < 2 ? "disabled" : ""}>Start game</button>
        </div>
      ` : ""}
    </section>
  `;
}

function renderApp() {
  if (!state.snapshot) {
    return renderLanding();
  }

  const snapshot = state.snapshot.data;
  const showMobileLobbyLayout = isMobileLobbyLayout(snapshot);
  const gameScreenClasses = [
    "game-screen",
    `players-${snapshot.players.length}`,
    isMobileActiveGameLayout(snapshot) ? "mobile-one-screen" : "",
    isMobileActiveGameLayout(snapshot) ? `layout-${tableLayoutVariant(snapshot)}` : "",
  ]
    .filter(Boolean)
    .join(" ");

  return `
    ${renderGameTopbar(snapshot)}
    <section class="${gameScreenClasses}">
      ${renderTable(snapshot)}
      ${showMobileLobbyLayout ? "" : renderActions(snapshot)}
    </section>
    ${!isMobileActiveGameLayout(snapshot) && state.error ? `<section class="panel error">${escapeHtml(state.error)}</section>` : ""}
    ${renderStandings(snapshot)}
  `;
}

function syncMobileGameLayout() {
  const root = document.documentElement;
  if (!document.body.classList.contains("game-active-mobile")) {
    root.style.removeProperty("--mobile-available-height");
    root.style.removeProperty("--mobile-topbar-height");
    root.style.removeProperty("--mobile-hand-height");
    root.style.removeProperty("--mobile-table-height");
    return;
  }

  const pageShell = document.querySelector(".page-shell");
  const appRoot = document.getElementById("app");
  const topbar = document.querySelector(".game-topbar");
  const gameScreen = document.querySelector(".game-screen.mobile-one-screen, .landing-screen");
  const handDock = document.querySelector(".hand-dock");

  if (!pageShell || !appRoot || !gameScreen) {
    return;
  }

  const shellRect = pageShell.getBoundingClientRect();
  const appStyles = window.getComputedStyle(appRoot);
  const appGap = Number.parseFloat(appStyles.rowGap || appStyles.gap || "0") || 0;
  const screenStyles = window.getComputedStyle(gameScreen);
  const screenGap = Number.parseFloat(screenStyles.rowGap || screenStyles.gap || "0") || 0;
  const topbarHeight = topbar?.getBoundingClientRect().height || 0;
  const handHeight = handDock?.getBoundingClientRect().height || 0;
  const availableHeight = Math.max(0, shellRect.height - topbarHeight - appGap);
  const tableHeight = handDock
    ? Math.max(0, availableHeight - handHeight - screenGap)
    : availableHeight;

  root.style.setProperty("--mobile-available-height", `${Math.round(availableHeight)}px`);
  root.style.setProperty("--mobile-topbar-height", `${Math.round(topbarHeight)}px`);
  root.style.setProperty("--mobile-hand-height", `${Math.round(handHeight)}px`);
  root.style.setProperty("--mobile-table-height", `${Math.round(tableHeight)}px`);
}

function wireEvents() {
  app.querySelectorAll("form").forEach((form) => form.addEventListener("submit", onSubmit));

  const handFan = app.querySelector(".hand-fan");
  if (handFan) {
    let touchStartX = null;
    let touchStartY = null;

    handFan.addEventListener("touchstart", (event) => {
      const touch = event.touches[0];
      if (!touch) {
        return;
      }
      touchStartX = touch.clientX;
      touchStartY = touch.clientY;
    }, { passive: true });

    handFan.addEventListener("touchmove", (event) => {
      const touch = event.touches[0];
      if (!touch || touchStartX === null || touchStartY === null) {
        return;
      }
      const deltaX = Math.abs(touch.clientX - touchStartX);
      const deltaY = Math.abs(touch.clientY - touchStartY);
      if (deltaX > 10 && deltaX > deltaY) {
        state.suppressCardTapUntil = Date.now() + 250;
      }
    }, { passive: true });

    const clearTouchTrack = () => {
      touchStartX = null;
      touchStartY = null;
    };

    handFan.addEventListener("touchend", clearTouchTrack, { passive: true });
    handFan.addEventListener("touchcancel", clearTouchTrack, { passive: true });
  }

  app.querySelectorAll("[data-card-id]").forEach((button) => {
    button.addEventListener("click", () => {
      if (Date.now() < state.suppressCardTapUntil) {
        return;
      }
      const card = privateCards().find((entry) => cardId(entry) === button.dataset.cardId);
      if (card) {
        toggleCard(card);
      }
    });
  });

  const handPrimaryAction = document.getElementById("hand-primary-action");
  if (handPrimaryAction) {
    handPrimaryAction.addEventListener("click", () => {
      const { handAction } = handPrimaryAction.dataset;
      if (handAction === "choose-public") {
        submitChoosePublicCards();
      } else if (handAction === "play-cards") {
        submitPlayCards();
      } else if (handAction === "play-hidden") {
        submitHiddenCard();
      } else if (handAction === "resolve-joker") {
        submitResolveJoker();
      }
    });
  }

  const takePile = document.getElementById("take-pile");
  if (takePile) {
    takePile.addEventListener("click", submitTakePile);
  }

  const takePileOverlay = document.getElementById("take-pile-overlay");
  if (takePileOverlay) {
    takePileOverlay.addEventListener("click", submitTakePile);
  }

  const playHidden = document.getElementById("play-hidden");
  if (playHidden) {
    playHidden.addEventListener("click", submitHiddenCard);
  }

  app.querySelectorAll("[data-joker-rank]").forEach((button) => {
    button.addEventListener("click", () => {
      state.jokerRank = Number(button.dataset.jokerRank);
      if (state.jokerRank !== state.snapshot?.data?.rules.high_low_rank) {
        state.highLowChoice = "";
      }
      state.error = "";
      render();
    });
  });

  const chooseHigher = document.getElementById("choose-higher");
  if (chooseHigher) {
    chooseHigher.addEventListener("click", () => {
      state.highLowChoice = "HIGHER";
      state.error = "";
      render();
    });
  }

  const chooseLower = document.getElementById("choose-lower");
  if (chooseLower) {
    chooseLower.addEventListener("click", () => {
      state.highLowChoice = "LOWER";
      state.error = "";
      render();
    });
  }

  const startButton = document.getElementById("start-game");
  if (startButton) {
    startButton.addEventListener("click", startGame);
  }

  const copyInviteCodeButton = document.getElementById("copy-invite-code");
  if (copyInviteCodeButton) {
    copyInviteCodeButton.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(state.inviteCode);
        state.error = "Invite code copied.";
      } catch (error) {
        state.error = "Copy failed. You can still share the code manually.";
      }
      render();
    });
  }

  const restoreSessionButton = document.getElementById("restore-session");
  if (restoreSessionButton) {
    restoreSessionButton.addEventListener("click", () => {
      restoreSession({ resetRetry: true });
    });
  }

  app.querySelectorAll("[data-landing-bucket]").forEach((button) => {
    button.addEventListener("click", () => {
      toggleLandingBucket(button.dataset.landingBucket);
    });
  });

  const forgetSessionButton = document.getElementById("forget-session");
  if (forgetSessionButton) {
    forgetSessionButton.addEventListener("click", forgetSavedSession);
  }

  const shareInviteButton = document.getElementById("share-invite");
  if (shareInviteButton) {
    shareInviteButton.addEventListener("click", async () => {
      const inviteUrl = buildInviteLink();
      try {
        if (typeof navigator.share === "function") {
          await navigator.share({
            title: "Shithead invite",
            text: `Join my Shithead game with invite code ${state.inviteCode}.`,
            url: inviteUrl,
          });
          state.error = "Invite link shared.";
        } else {
          await navigator.clipboard.writeText(inviteUrl);
          state.error = "Invite link copied.";
        }
      } catch (error) {
        try {
          await navigator.clipboard.writeText(inviteUrl);
          state.error = "Invite link copied.";
        } catch (clipboardError) {
          state.error = "Share failed. You can still share the invite link manually.";
        }
      }
      render();
    });
  }

  const openRulesMenuButton = document.getElementById("open-rules-menu");
  if (openRulesMenuButton) {
    openRulesMenuButton.addEventListener("click", openRulesMenu);
  }

  const closeRulesMenuButton = document.getElementById("close-rules-menu");
  if (closeRulesMenuButton) {
    closeRulesMenuButton.addEventListener("click", closeRulesMenu);
  }

  const closeRulesMenuBackdrop = document.getElementById("close-rules-menu-backdrop");
  if (closeRulesMenuBackdrop) {
    closeRulesMenuBackdrop.addEventListener("click", closeRulesMenu);
  }

  const leaveButton = document.getElementById("leave-game");
  if (leaveButton) {
    leaveButton.addEventListener("click", clearSession);
  }

  const headerLeaveButton = document.getElementById("leave-game-header");
  if (headerLeaveButton) {
    headerLeaveButton.addEventListener("click", handleLeaveClick);
  } else {
    resetLeaveConfirmation();
  }
}

function render() {
  document.body.classList.toggle("game-active-mobile", !state.snapshot || isMobileActiveGameLayout());
  document.body.classList.toggle(
    "game-started-mobile",
    isMobileActiveGameLayout() && state.snapshot?.data?.status !== "LOBBY",
  );
  app.innerHTML = renderApp();
  if (!state.snapshot && state.pendingLandingNameFocus) {
    const joinNameInput = document.getElementById("join-name");
    if (joinNameInput) {
      joinNameInput.focus();
      state.pendingLandingNameFocus = false;
    }
  }
  wireEvents();
  window.requestAnimationFrame(syncMobileGameLayout);
}

loadStoredSession();
loadInviteLink();
render();
restoreSession();

window.addEventListener("pageshow", () => {
  attemptSessionRecovery({ resetRetry: true });
});

window.addEventListener("focus", () => {
  attemptSessionRecovery({ resetRetry: true });
});

window.addEventListener("online", () => {
  attemptSessionRecovery({ resetRetry: true });
});

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") {
    attemptSessionRecovery({ resetRetry: true });
  }
});

window.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && state.rulesMenuOpen) {
    closeRulesMenu();
  }
});

window.addEventListener("resize", () => {
  if (state.snapshot) {
    render();
  }
});

window.addEventListener("orientationchange", () => {
  if (state.snapshot) {
    render();
  }
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/static/sw.js?v=20260329m").then(() => {
    if (navigator.serviceWorker.controller) {
      navigator.serviceWorker.addEventListener("controllerchange", () => {
        window.location.reload();
      });
    }
  }).catch(() => {});
}
