const storageKey = "shithead.alpha.session";
const playPilePreviewLimit = 6;

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

function clearReconnectTimer() {
  if (state.reconnectTimer !== null) {
    window.clearTimeout(state.reconnectTimer);
    state.reconnectTimer = null;
  }
}

function clearTurnNoticeTimer() {
  if (state.turnNoticeTimer !== null) {
    window.clearTimeout(state.turnNoticeTimer);
    state.turnNoticeTimer = null;
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
  persistSession();
  render();
}

function cardId(card) {
  return `${card.rank}-${card.suit}`;
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
  };
  return map[rank] || String(rank);
}

function suitLabel(suit) {
  const map = {
    1: "&diams;",
    2: "&hearts;",
    3: "&clubs;",
    4: "&spades;",
  };
  return map[suit] || "?";
}

function isRedSuit(suit) {
  return suit === 1 || suit === 2;
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
  return privateCards().some((card) => validRanks.has(card.rank));
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
  return state.selectedCards[0].rank;
}

function resetSelection() {
  state.selectedCards = [];
  state.highLowChoice = "";
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
    if (state.selectedCards.length === 0 || selectedRank() === card.rank) {
      state.selectedCards = [...state.selectedCards, card];
      state.error = "";
    } else {
      state.error = "You can only select cards of the same rank.";
    }
    render();
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Request failed.");
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

async function restoreSession() {
  if (!state.inviteCode || !state.playerToken) {
    return;
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
    clearSession("Your saved session is no longer available. Join the game again if it is still active.");
  }
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
  if (
    selectedRank() === state.snapshot.data.rules.high_low_rank &&
    !["HIGHER", "LOWER"].includes(state.highLowChoice)
  ) {
    state.error = "Choose whether the next player must go higher or may go lower.";
    render();
    return;
  }
  sendAction({
    type: "play_private_cards",
    cards: state.selectedCards,
    choice: selectedRank() === state.snapshot.data.rules.high_low_rank ? state.highLowChoice : "",
  });
  resetSelection();
}

function submitTakePile() {
  sendAction({ type: "take_play_pile" });
}

function submitHiddenCard() {
  sendAction({ type: "play_hidden_card" });
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
  if (isRedSuit(card.suit)) {
    classes.push("red");
  }
  const disabled = clickable ? "" : "disabled";
  return `
    <button class="${classes.join(" ")}" data-card-id="${cardId(card)}" ${disabled}>
      <span class="card-rank">${rankLabel(card.rank)}</span>
      <span class="card-suit">${suitLabel(card.suit)}</span>
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
    4: ["seat-bottom", "seat-left", "seat-top", "seat-right"],
  };
  return layouts[snapshot.players.length]?.[relativeIndex] || "seat-top";
}

function renderPublicCardChips(publicCards) {
  if (publicCards.length === 0) {
    return '<span class="seat-muted">No public cards</span>';
  }
  return publicCards
    .map(
      (card) => `
        <span class="public-card-chip ${isRedSuit(card.suit) ? "red" : ""}">
          ${rankLabel(card.rank)}${suitLabel(card.suit)}
        </span>
      `,
    )
    .join("");
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
      <div class="seat-header">
        <div class="seat-title-row">
          <strong>${escapeHtml(player.display_name)}</strong>
          <div class="seat-badges">${seatBadges}</div>
        </div>
      </div>
      <div class="seat-counts">
        <span>Hand ${player.private_cards_count}</span>
        <span>Hidden ${player.hidden_cards_count}</span>
      </div>
      <div class="seat-public-cards">${renderPublicCardChips(player.public_cards)}</div>
    </div>
  `;
}

function renderMiniCard(card) {
  return `
    <div class="mini-card ${isRedSuit(card.suit) ? "red" : ""}">
      <span>${rankLabel(card.rank)}</span>
      <span>${suitLabel(card.suit)}</span>
    </div>
  `;
}

function renderPilePreview(playPile) {
  if (playPile.length === 0) {
    return '<div class="pile-empty">Empty</div>';
  }
  return playPile
    .slice(0, playPilePreviewLimit)
    .reverse()
    .map((card) => renderMiniCard(card))
    .join("");
}

function playPileCaption(playPile) {
  if (playPile.length === 0) {
    return "No cards";
  }
  if (playPile.length > playPilePreviewLimit) {
    const hiddenCount = playPile.length - playPilePreviewLimit;
    return `+${hiddenCount} card${hiddenCount === 1 ? "" : "s"}`;
  }
  return `${playPile.length} card${playPile.length === 1 ? "" : "s"}`;
}

function isMobileActiveGameLayout(snapshot = state.snapshot?.data) {
  return Boolean(snapshot) && snapshot.status !== "GAME_OVER" && window.innerWidth < 720;
}

function isMobileLobbyLayout(snapshot = state.snapshot?.data) {
  return isMobileActiveGameLayout(snapshot) && snapshot.status === "LOBBY";
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
    if (selectedRank() === snapshot.rules.high_low_rank) {
      return "Choose how the 7 changes the next player's turn.";
    }
    if (canPlayHiddenCard()) {
      return "Your hidden cards are live. Take a hidden card.";
    }
    if (mustTakePile(snapshot)) {
      return "No legal card to play. Take the pile.";
    }
    return "Tap matching cards from your hand, then play them.";
  }
  if (currentGameState() === "DURING_GAME") {
    return `Waiting for ${turnTarget} to play.`;
  }
  return "Waiting for the game to begin.";
}

function renderLanding() {
  return `
    ${state.restoringSession ? `
      <section class="panel stack">
        <h2>Restoring your game</h2>
        <p class="muted">Reclaiming your seat and reconnecting to live updates.</p>
      </section>
    ` : ""}
    ${state.error ? `<section class="panel error">${escapeHtml(state.error)}</section>` : ""}
    <section class="panel alpha-note stack">
      <h2>Alpha notice</h2>
      <p class="muted">
        This release is running as a small public alpha. Keep the tab open while you play.
      </p>
      <p class="muted">
        Live games can reset after a deploy, restart, or idle spin-down on the hosting service.
      </p>
    </section>
    <section class="grid-two">
      <article class="panel stack">
        <h2>Create a table</h2>
        <p class="muted">Start a private lobby and get an invite code for the other players.</p>
        <form class="stack" data-mode="create">
          <div class="field">
            <label for="create-name">Display name</label>
            <input id="create-name" name="display_name" maxlength="24" required placeholder="Johannes" />
          </div>
          <button class="button accent" type="submit">Create game</button>
        </form>
      </article>
      <article class="panel stack">
        <h2>Join a table</h2>
        <p class="muted">Enter the invite code and your display name to claim a seat.</p>
        <form class="stack" data-mode="join">
          <div class="field">
            <label for="join-code">Invite code</label>
            <input id="join-code" name="invite_code" maxlength="6" required placeholder="AB12CD" />
          </div>
          <div class="field">
            <label for="join-name">Display name</label>
            <input id="join-name" name="display_name" maxlength="24" required placeholder="Mira" />
          </div>
          <button class="button" type="submit">Join game</button>
        </form>
      </article>
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
  const showHighLowChoice = selectedRank() === snapshot.rules.high_low_rank;
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
  );
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
        <div>
          <p class="section-title">Your hand</p>
        </div>
      </div>
      <div class="dock-prompt">${escapeHtml(currentPrompt(snapshot))}</div>
      ${state.error ? `<div class="dock-error">${escapeHtml(state.error)}</div>` : ""}
      <div class="hand-fan">
        ${
          cards.map((card) => renderCard(card, selectedIds.has(cardId(card)))).join("")
            || '<p class="muted">No cards in hand right now.</p>'
        }
      </div>
      <div class="actions">
        ${canChoosePublicCards() ? `
          <div class="primary-action-row">
            <button class="button accent full-width" id="choose-public">Lock selected public cards</button>
          </div>
        ` : ""}
        ${showPlaySelectedAction ? `
          <div class="primary-action-row">
            <button class="button accent full-width" id="play-cards" ${cards.length === 0 || (showHighLowChoice && !hasHighLowChoice) ? "disabled" : ""}>${showHighLowChoice && !hasHighLowChoice ? "Choose higher or lower first" : "Play selected cards"}</button>
          </div>
        ` : ""}
        ${showHiddenAction ? `
          <div class="primary-action-row">
            <button class="button accent full-width" id="play-hidden-primary">Take hidden card</button>
          </div>
        ` : ""}
        ${showHighLowChoice ? `
          <div class="choice-block">
            <div class="choice-row">
              <button class="button ${state.highLowChoice === "HIGHER" ? "accent" : "secondary"}" id="choose-higher">7 or higher</button>
              <button class="button ${state.highLowChoice === "LOWER" ? "accent" : "secondary"}" id="choose-lower">7 or lower</button>
            </div>
          </div>
        ` : ""}
        ${currentGameState() === "DURING_GAME" && !isMyTurn() && !showMobileTurnPrompt ? `<p class="muted tiny">Waiting for ${escapeHtml(turnName)}.</p>` : ""}
      </div>
      <details class="help-drawer">
        <summary>Rules and controls</summary>
        <div class="help-copy stack">
          <p class="muted">Pick 3 public cards first. After that, tap matching ranks in your hand and use the main play button.</p>
          <p class="muted">7 changes the next player's direction, 8 skips, 10 burns, and hidden cards are only available when the hand is empty.</p>
        </div>
      </details>
    </section>
  `;
}

function renderGameTopbar(snapshot) {
  if (!snapshot) {
    return "";
  }
  const showCompactBrand = isMobileActiveGameLayout(snapshot);

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
        <button class="button secondary button-inline" id="leave-game-header">Leave</button>
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

function renderTable(snapshot) {
  const self = me();
  const isHost = self && self.is_host;
  const activeTurnName = snapshot.current_turn_display_name || turnPlayer()?.display_name || null;
  const winningPlayer = winner();
  const showLobbyControls = snapshot.status === "LOBBY";
  const showMobileLobbyLayout = isMobileLobbyLayout(snapshot);
  const sortedPlayers = [...snapshot.players].sort(
    (left, right) => relativeSeatIndex(snapshot, left) - relativeSeatIndex(snapshot, right),
  );

  let turnHeadline = "Waiting in lobby";
  let turnCopy = currentPrompt(snapshot);
  if (snapshot.status === "GAME_OVER") {
    turnHeadline = `${winningPlayer?.display_name || "A player"} won`;
  } else if (snapshot.game_state) {
    turnHeadline = isMyTurn() ? "Your turn" : `${activeTurnName} is up`;
  }

  const lobbyControls = showLobbyControls ? `
    <span class="invite-code">Invite code ${snapshot.invite_code}</span>
    <button class="button secondary" id="copy-code">Copy code</button>
  ` : "";

  return `
    <section class="panel table-stage stack">
      ${showLobbyControls && !showMobileLobbyLayout ? `
        <div class="controls">
          ${lobbyControls}
        </div>
      ` : ""}
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
          ${!isMobileActiveGameLayout(snapshot) ? `
            <div class="turn-banner">
              <span class="section-title">Turn</span>
              <strong>${escapeHtml(turnHeadline)}</strong>
              <span class="muted">${escapeHtml(turnCopy)}</span>
            </div>
          ` : ""}
          ${snapshot.status_message ? `
            <div class="event-box">
              <strong>Play Update</strong>
              <span>${escapeHtml(snapshot.status_message)}</span>
            </div>
          ` : ""}
          <div class="table-resources">
            <div class="deck-orb">
              <span class="resource-label">Deck</span>
              <strong>${snapshot.cards_in_deck}</strong>
            </div>
            <div class="pile-zone">
              <span class="resource-label">Play pile</span>
              <div class="pile-preview">${renderPilePreview(snapshot.play_pile)}</div>
              <span class="pile-caption">${playPileCaption(snapshot.play_pile)}</span>
              ${renderPileAction(snapshot)}
            </div>
          </div>
        </div>
      </div>
      <div class="table-meta">
        <div class="stack-card">
          <strong>Rules</strong>
          <span>7 changes direction. 8 skips. 10 burns. Hidden cards go live last.</span>
        </div>
        <div class="stack-card">
          <strong>Table pulse</strong>
          <span>The glowing seat is the active player. Bright event text marks burns, skips, and pile takes.</span>
        </div>
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
  if (!isMobileActiveGameLayout()) {
    root.style.removeProperty("--mobile-available-height");
    root.style.removeProperty("--mobile-topbar-height");
    root.style.removeProperty("--mobile-hand-height");
    root.style.removeProperty("--mobile-table-height");
    return;
  }

  const pageShell = document.querySelector(".page-shell");
  const appRoot = document.getElementById("app");
  const topbar = document.querySelector(".game-topbar");
  const gameScreen = document.querySelector(".game-screen.mobile-one-screen");
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
  const tableHeight = Math.max(0, availableHeight - handHeight - screenGap);

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

  const choosePublic = document.getElementById("choose-public");
  if (choosePublic) {
    choosePublic.addEventListener("click", submitChoosePublicCards);
  }

  const playCards = document.getElementById("play-cards");
  if (playCards) {
    playCards.addEventListener("click", submitPlayCards);
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

  const playHiddenPrimary = document.getElementById("play-hidden-primary");
  if (playHiddenPrimary) {
    playHiddenPrimary.addEventListener("click", submitHiddenCard);
  }

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

  const copyCodeButton = document.getElementById("copy-code");
  if (copyCodeButton) {
    copyCodeButton.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(state.inviteCode);
        state.error = "Invite code copied.";
      } catch (error) {
        state.error = "Copy failed. You can still share the code manually.";
      }
      render();
    });
  }

  const leaveButton = document.getElementById("leave-game");
  if (leaveButton) {
    leaveButton.addEventListener("click", clearSession);
  }

  const headerLeaveButton = document.getElementById("leave-game-header");
  if (headerLeaveButton) {
    headerLeaveButton.addEventListener("click", clearSession);
  }
}

function render() {
  document.body.classList.toggle("game-active-mobile", isMobileActiveGameLayout());
  document.body.classList.toggle(
    "game-started-mobile",
    isMobileActiveGameLayout() && state.snapshot?.data?.status !== "LOBBY",
  );
  app.innerHTML = renderApp();
  wireEvents();
  window.requestAnimationFrame(syncMobileGameLayout);
}

loadStoredSession();
render();
restoreSession();

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
  navigator.serviceWorker.register("/static/sw.js").then(() => {
    if (navigator.serviceWorker.controller) {
      navigator.serviceWorker.addEventListener("controllerchange", () => {
        window.location.reload();
      });
    }
  }).catch(() => {});
}
