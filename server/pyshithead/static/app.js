const storageKey = "shithead.alpha.session";

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
  selectedCards: [],
  highLowChoice: "",
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

function clearSession() {
  if (state.ws) {
    state.ws.close();
  }
  state.inviteCode = "";
  state.playerToken = "";
  state.seat = null;
  state.displayName = "";
  state.snapshot = null;
  state.privateState = null;
  state.error = "";
  state.ws = null;
  state.wsReady = false;
  state.selectedCards = [];
  state.highLowChoice = "";
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
  persistSession();
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
  try {
    const response = await api(`/api/games/${state.inviteCode}`);
    state.snapshot = response;
    connectWebSocket();
  } catch (error) {
    clearSession();
  }
}

function connectWebSocket() {
  if (!state.inviteCode || !state.playerToken) {
    return;
  }
  if (state.ws && [WebSocket.OPEN, WebSocket.CONNECTING].includes(state.ws.readyState)) {
    return;
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(
    `${protocol}//${window.location.host}/api/games/${state.inviteCode}/ws?token=${encodeURIComponent(state.playerToken)}`,
  );

  ws.addEventListener("open", () => {
    state.wsReady = true;
    state.error = "";
    render();
  });

  ws.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "session_snapshot") {
      state.snapshot = payload;
      if (!payload.data.players.some((player) => player.seat === state.seat)) {
        clearSession();
        return;
      }
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

  ws.addEventListener("close", () => {
    state.wsReady = false;
    render();
    if (state.playerToken) {
      window.setTimeout(connectWebSocket, 1200);
    }
  });

  state.ws = ws;
}

async function startGame() {
  try {
    const response = await api(`/api/games/${state.inviteCode}/start`, {
      method: "POST",
      body: JSON.stringify({ player_token: state.playerToken }),
    });
    state.snapshot = response;
    state.error = "";
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

function renderLanding() {
  return `
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
                <strong>${ordinal(player.finished_position)} - ${player.display_name}</strong>
                <span>${player.seat === state.seat ? "You" : `Seat ${player.seat}`}</span>
              </div>
            `,
          )
          .join("")}
      </div>
    </section>
  `;
}

function renderPlayers(snapshot) {
  return snapshot.players
    .map((player) => {
      const isCurrentTurn = player.seat === snapshot.current_turn_seat;
      const isWinner = player.finished_position === 1;
      const badges = [
        player.is_host ? "Host" : "",
        player.is_connected ? "Connected" : "Disconnected",
        player.has_finished ? "Finished" : "",
        player.seat === state.seat ? "You" : "",
        isCurrentTurn ? "Current turn" : "",
      ].filter(Boolean);

      return `
        <div class="panel stack player-panel ${isCurrentTurn ? "current-turn" : ""} ${isWinner ? "winner" : ""}">
          <div>
            <h3>${player.display_name}</h3>
            <div class="chip-row">${badges.map((badge) => `<span class="player-chip">${badge}</span>`).join("")}</div>
          </div>
          ${player.finished_position ? `<div class="placement">${ordinal(player.finished_position)} place</div>` : ""}
          <div class="muted tiny">Seat ${player.seat}</div>
          <div class="tiny">Public cards: ${player.public_cards.map((card) => `${rankLabel(card.rank)}${suitLabel(card.suit)}`).join(" ") || "None yet"}</div>
          <div class="tiny">Private cards: ${player.private_cards_count}</div>
          <div class="tiny">Hidden cards: ${player.hidden_cards_count}</div>
        </div>
      `;
    })
    .join("");
}

function renderActions(snapshot) {
  if (snapshot.status === "GAME_OVER") {
    return "";
  }

  const cards = privateCards();
  const selectedIds = new Set(state.selectedCards.map((card) => cardId(card)));
  const showHighLowChoice = selectedRank() === snapshot.rules.high_low_rank;
  const hasHighLowChoice = ["HIGHER", "LOWER"].includes(state.highLowChoice);
  const turnName = snapshot.current_turn_display_name || `Seat ${snapshot.current_turn_seat}`;

  return `
    <section class="panel stack">
      <div>
        <p class="section-title">Your hand</p>
        <div class="card-grid">
          ${cards.map((card) => renderCard(card, selectedIds.has(cardId(card)))).join("") || '<p class="muted">No private cards in hand.</p>'}
        </div>
      </div>
      <div class="actions">
        ${canChoosePublicCards() ? `
          <div class="action-row">
            <button class="button accent" id="choose-public">Lock selected public cards</button>
            <button class="button secondary" id="clear-selection">Clear selection</button>
          </div>
          <p class="muted tiny">Pick exactly 3 cards. These become your revealed cards for the table.</p>
        ` : ""}
        ${currentGameState() === "DURING_GAME" && isMyTurn() ? `
          <div class="action-row">
            <button class="button accent" id="play-cards" ${cards.length === 0 || (showHighLowChoice && !hasHighLowChoice) ? "disabled" : ""}>${showHighLowChoice && !hasHighLowChoice ? "Choose higher or lower first" : "Play selected cards"}</button>
            <button class="button secondary" id="take-pile">Take pile</button>
            <button class="button secondary" id="play-hidden" ${canPlayHiddenCard() ? "" : "disabled"}>Play hidden card</button>
            <button class="button secondary" id="clear-selection">Clear selection</button>
          </div>
        ` : ""}
        ${showHighLowChoice ? `
          <p class="muted tiny">You selected a 7. Pick one before you can play it.</p>
          <div class="action-row">
            <button class="button ${state.highLowChoice === "HIGHER" ? "accent" : "secondary"}" id="choose-higher">Next player may play 7 or higher</button>
            <button class="button ${state.highLowChoice === "LOWER" ? "accent" : "secondary"}" id="choose-lower">Next player may play 7 or lower</button>
          </div>
        ` : ""}
        ${currentGameState() === "DURING_GAME" && !isMyTurn() ? `<p class="muted tiny">Waiting for ${turnName} to play.</p>` : ""}
      </div>
    </section>
  `;
}

function renderTable(snapshot) {
  const self = me();
  const isHost = self && self.is_host;
  const activeTurnName = snapshot.current_turn_display_name || turnPlayer()?.display_name || null;
  const winningPlayer = winner();

  let turnHeadline = "Waiting in lobby";
  let turnCopy = "Share the invite code and start once everyone has joined.";
  if (snapshot.status === "GAME_OVER") {
    turnHeadline = `${winningPlayer?.display_name || "A player"} won`;
    turnCopy = "Final standings are shown below.";
  } else if (snapshot.game_state) {
    turnHeadline = isMyTurn() ? "Your turn" : `${activeTurnName} is up`;
    turnCopy = isMyTurn()
      ? "Your cards are selectable below. Play now or take the pile if you are blocked."
      : "The highlighted player panel below shows whose turn it is.";
  }

  return `
    <section class="panel table-stage stack">
      <div class="controls">
        <span class="invite-code">Invite code ${snapshot.invite_code}</span>
        <span class="status-chip ${state.wsReady ? "live" : "wait"}">${state.wsReady ? "Live sync connected" : "Reconnecting"}</span>
        <button class="button secondary" id="copy-code">Copy code</button>
        <button class="button secondary" id="leave-game">Leave game</button>
      </div>
      <div class="turn-banner">
        <span class="section-title">Turn</span>
        <strong>${turnHeadline}</strong>
        <span class="muted">${turnCopy}</span>
      </div>
      ${snapshot.status_message ? `
        <div class="event-box">
          <strong>Play Update</strong>
          <span>${snapshot.status_message}</span>
        </div>
      ` : ""}
      <div class="status-strip">
        <span class="status-chip">${snapshot.status}</span>
        <span class="status-chip">${snapshot.game_state || "Waiting for host"}</span>
        ${activeTurnName ? `<span class="status-chip">Current player ${activeTurnName}</span>` : ""}
      </div>
      <div class="card-stack">
        <div class="stack-card deck-focus">
          <strong>Cards left in deck</strong>
          <span class="deck-number">${snapshot.cards_in_deck}</span>
        </div>
        <div class="stack-card">
          <strong>Play pile</strong>
          <span>${snapshot.play_pile.map((card) => `${rankLabel(card.rank)}${suitLabel(card.suit)}`).join(" ") || "Empty"}</span>
        </div>
        <div class="stack-card">
          <strong>Rules</strong>
          <span>7 sets the next player's direction. 10 burns. 8 skips.</span>
        </div>
      </div>
      ${snapshot.status === "LOBBY" && isHost ? `
        <div class="action-row">
          <button class="button accent" id="start-game" ${snapshot.players.length < 2 ? "disabled" : ""}>Start game</button>
        </div>
      ` : ""}
    </section>
  `;
}

function renderApp() {
  if (!state.snapshot) {
    return renderLanding();
  }

  return `
    ${renderTable(state.snapshot.data)}
    ${state.error ? `<section class="panel error">${state.error}</section>` : ""}
    ${renderStandings(state.snapshot.data)}
    ${renderActions(state.snapshot.data)}
    <section class="grid-two">
      <article class="panel stack">
        <h2>Players</h2>
        <div class="player-list">${renderPlayers(state.snapshot.data)}</div>
      </article>
      <article class="panel stack">
        <h2>How this alpha works</h2>
        <p class="muted">Create or join with an invite code, keep the tab open, and reconnect automatically after a reload.</p>
        <p class="muted">This alpha runs on a single live server. A deploy, restart, or long idle period can interrupt active games.</p>
        <p class="muted">Public cards are selected first. During the game, play equal-ranked private cards, take the pile if needed, and use the hidden-card action only when available.</p>
      </article>
    </section>
  `;
}

function wireEvents() {
  app.querySelectorAll("form").forEach((form) => form.addEventListener("submit", onSubmit));

  app.querySelectorAll("[data-card-id]").forEach((button) => {
    button.addEventListener("click", () => {
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

  const playHidden = document.getElementById("play-hidden");
  if (playHidden) {
    playHidden.addEventListener("click", submitHiddenCard);
  }

  const clearSelectionButton = document.getElementById("clear-selection");
  if (clearSelectionButton) {
    clearSelectionButton.addEventListener("click", () => {
      resetSelection();
      render();
    });
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
}

function render() {
  app.innerHTML = renderApp();
  wireEvents();
}

loadStoredSession();
render();
restoreSession();

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/static/sw.js").then(() => {
    if (navigator.serviceWorker.controller) {
      navigator.serviceWorker.addEventListener("controllerchange", () => {
        window.location.reload();
      });
    }
  }).catch(() => {});
}
