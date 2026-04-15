import {
  isJokerCard,
  JOKER_SYMBOL as jokerSymbol,
} from "../gameplay_ui_state.js";

const playPilePreviewLimit = 6;

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

function playerForSeat(snapshot, seat) {
  return snapshot?.players?.find((player) => player.seat === seat) || null;
}

function parseTimestamp(value) {
  if (!value) {
    return null;
  }
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatDuration(totalSeconds) {
  const seconds = Math.max(0, Math.round(totalSeconds));
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  if (minutes < 60) {
    return remainder === 0 ? `${minutes}m` : `${minutes}m ${remainder}s`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes === 0
    ? `${hours}h`
    : `${hours}h ${remainingMinutes}m`;
}

function disconnectActionLabel(action) {
  if (action === "AUTO_PLAY_TURN") {
    return "Auto-play turn";
  }
  if (action === "AUTO_REMOVE_SETUP") {
    return "Auto-remove";
  }
  return "";
}

function canHostRemovePlayer(snapshot, localSeat, player) {
  const self = playerForSeat(snapshot, localSeat);
  return Boolean(
    self && self.is_host && !player.is_host && !player.is_connected,
  );
}

function placementBadgeForPlayer(snapshot, player) {
  if (player.finished_position == null) {
    return null;
  }

  if (player.finished_position === 1) {
    return {
      label: "1st 👑",
      classes: ["seat-badge-placement", "seat-badge-winner"],
    };
  }

  if (
    snapshot.status === "GAME_OVER" &&
    player.finished_position === snapshot.players.length
  ) {
    return {
      label: "Shithead 💩",
      classes: ["seat-badge-placement", "seat-badge-shithead"],
    };
  }

  return {
    label: ordinal(player.finished_position),
    classes: ["seat-badge-placement"],
  };
}

function renderOfflinePresence({
  player,
  snapshot,
  localSeat,
  presenceNow,
  kickSeatArmed,
}) {
  if (player.is_connected) {
    return "";
  }

  const lines = [];
  const nowMs = presenceNow || Date.now();
  const lastSeenMs = parseTimestamp(player.last_seen_at);
  if (lastSeenMs !== null) {
    lines.push(`Offline for ${formatDuration((nowMs - lastSeenMs) / 1000)}`);
  } else {
    lines.push("Offline");
  }

  const deadlineMs = parseTimestamp(player.disconnect_deadline_at);
  if (deadlineMs !== null && player.disconnect_action) {
    lines.push(
      `${disconnectActionLabel(player.disconnect_action)} in ${formatDuration((deadlineMs - nowMs) / 1000)}`,
    );
  } else if (canHostRemovePlayer(snapshot, localSeat, player)) {
    lines.push("Waiting for reconnect. Host can remove now.");
  } else {
    lines.push("Waiting for reconnect.");
  }

  const armed = kickSeatArmed === player.seat;
  const removeButton = canHostRemovePlayer(snapshot, localSeat, player)
    ? `
      <button
        class="button secondary button-inline seat-remove-button ${armed ? "armed-remove" : ""}"
        type="button"
        data-kick-seat="${player.seat}"
        title="${armed ? "Click again to remove" : "Remove offline player"}"
        aria-label="${armed ? "Click again to remove" : "Remove offline player"}"
      >${armed ? "Confirm remove" : "Remove"}</button>
    `
    : "";

  return `
    <div class="seat-presence">
      ${lines.map((line) => `<span class="seat-presence-line">${escapeHtml(line)}</span>`).join("")}
      ${removeButton ? `<div class="seat-actions">${removeButton}</div>` : ""}
    </div>
  `;
}

function relativeSeatIndex(snapshot, localSeat, player) {
  if (!Number.isInteger(localSeat) || snapshot.players.length === 0) {
    return player.seat;
  }
  return (
    (player.seat - localSeat + snapshot.players.length) %
    snapshot.players.length
  );
}

function seatPositionClass(snapshot, localSeat, player) {
  const relativeIndex = relativeSeatIndex(snapshot, localSeat, player);
  const layouts = {
    1: ["seat-bottom"],
    2: ["seat-bottom", "seat-top"],
    3: ["seat-bottom", "seat-top-left", "seat-top-right"],
    4: ["seat-bottom", "seat-top-left", "seat-top", "seat-top-right"],
  };
  return layouts[snapshot.players.length]?.[relativeIndex] || "seat-top";
}

function shoutoutOffsetForSeat(snapshot, localSeat, player) {
  const position = seatPositionClass(snapshot, localSeat, player);
  if (position === "seat-bottom") {
    return { dx: 0, dy: -94 };
  }
  if (position === "seat-top") {
    return { dx: 0, dy: 92 };
  }
  if (position === "seat-top-left") {
    return { dx: 74, dy: 74 };
  }
  if (position === "seat-top-right") {
    return { dx: -74, dy: 74 };
  }
  if (position === "seat-left") {
    return { dx: 96, dy: 0 };
  }
  if (position === "seat-right") {
    return { dx: -96, dy: 0 };
  }
  if (position === "seat-bottom-left") {
    return { dx: 74, dy: -74 };
  }
  return { dx: 0, dy: -84 };
}

function hasActiveMotion(animations, kind) {
  return animations.some((animation) => animation.kind === kind);
}

function seatHasActiveMotion(animations, seat, kinds) {
  return animations.some(
    (animation) => kinds.includes(animation.kind) && animation.seat === seat,
  );
}

function renderCardBody(card) {
  const rankMarkup = isJokerCard(card) ? jokerSymbol : rankLabel(card.rank);
  return `
    <span class="card-rank">${rankMarkup}</span>
    ${
      isJokerCard(card)
        ? `<span class="card-joker-tag">${card.effective_rank ? `as ${rankLabel(card.effective_rank)}` : "wild"}</span>`
        : `<span class="card-suit">${suitLabel(card.suit)}</span>`
    }
  `;
}

function renderCard(card, selected, clickable = true, hidden = false) {
  const classes = ["card"];
  if (selected) {
    classes.push("selected");
  }
  if (hidden) {
    classes.push("local-play-hidden");
  }
  if (isJokerCard(card)) {
    classes.push("joker");
  }
  if (isRedSuit(card.suit)) {
    classes.push("red");
  }
  const disabled = clickable ? "" : "disabled";
  return `
    <button type="button" class="${classes.join(" ")}" data-card-id="${cardId(card)}" ${disabled}>
      ${renderCardBody(card)}
    </button>
  `;
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
    return "";
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
      <span class="seat-mini-suit">${isJoker ? (card.effective_rank ? rankLabel(card.effective_rank) : "?") : suitLabel(card.suit)}</span>
    </span>
  `;
}

function renderSeatPublicStack(publicCards, hiddenCardsCount) {
  if (publicCards.length === 0) {
    return hiddenCardsCount > 0 ? renderSeatHiddenStack(hiddenCardsCount) : "";
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

function renderSeatShoutouts({
  snapshot,
  player,
  localSeat,
  shoutouts = [],
}) {
  if (!Array.isArray(shoutouts) || shoutouts.length === 0) {
    return "";
  }

  const offset = shoutoutOffsetForSeat(snapshot, localSeat, player);
  return shoutouts
    .map(
      (shoutout) => `
        <span
          class="motion-shoutout motion-shoutout-${escapeHtml(
            shoutout.presetKey || shoutout.source || "default",
          )}"
          data-shoutout-id="${escapeHtml(shoutout.id || "")}"
          data-shoutout-event-id="${escapeHtml(shoutout.eventId || "")}"
          data-shoutout-key="${escapeHtml(shoutout.presetKey || "")}"
          data-shoutout-source="${escapeHtml(shoutout.source || "preset")}"
          style="
            left:50%;
            top:50%;
            --shoutout-dx:${Math.round(offset.dx)}px;
            --shoutout-dy:${Math.round(offset.dy)}px;
            --shoutout-dx-soft:${Math.round(offset.dx * 0.72)}px;
            --shoutout-dy-soft:${Math.round(offset.dy * 0.72)}px;
            --shoutout-accent:${escapeHtml(shoutout.accentColor || "#f4b942")};
            --shoutout-duration:${Math.max(0, shoutout.durationMs || 1500)}ms;
          "
          aria-hidden="true"
        >
          <span class="motion-shoutout-body ${shoutout.emoji ? "" : "no-emoji"}">
            <span class="motion-shoutout-emoji ${shoutout.source === "custom" ? "custom" : ""}">${escapeHtml(shoutout.emoji || "✨")}</span>
            <span class="motion-shoutout-label">${escapeHtml(shoutout.text || "Shoutout")}</span>
          </span>
        </span>
      `,
    )
    .join("");
}

function renderSeatShoutoutReplayBadge({ seat, shoutout = null }) {
  if (!shoutout) {
    return "";
  }

  return `
    <button
      class="seat-badge seat-badge-meta seat-shoutout-replay-badge"
      type="button"
      data-shoutout-history-seat="${seat}"
      title="${escapeHtml(`Replay shoutout: ${shoutout.text || "Shoutout"}`)}"
      aria-label="${escapeHtml(`Replay shoutout: ${shoutout.text || "Shoutout"}`)}"
    >
      ${
        shoutout.emoji
          ? `<span class="seat-shoutout-replay-emoji">${escapeHtml(shoutout.emoji)}</span>`
          : '<span class="seat-shoutout-replay-dot" aria-hidden="true"></span>'
      }
    </button>
  `;
}

const winnerFireworkBursts = Object.freeze([
  {
    key: "north-west",
    left: "17%",
    top: "10%",
    delayMs: 0,
    sparks: [
      { x: 0, y: -38, color: "#ffe89c" },
      { x: 31, y: -18, color: "#fff8d9" },
      { x: 34, y: 13, color: "#f6b744" },
      { x: 0, y: 34, color: "#ffd972" },
      { x: -31, y: 17, color: "#fff3c0" },
      { x: -33, y: -15, color: "#e7a73c" },
    ],
  },
  {
    key: "north-east",
    left: "84%",
    top: "16%",
    delayMs: 180,
    sparks: [
      { x: 0, y: -34, color: "#fff6cf" },
      { x: 28, y: -15, color: "#ffd36a" },
      { x: 33, y: 15, color: "#fff8e1" },
      { x: 0, y: 31, color: "#f4ba53" },
      { x: -29, y: 17, color: "#ffd876" },
      { x: -31, y: -14, color: "#fff0a9" },
    ],
  },
  {
    key: "south",
    left: "50%",
    top: "92%",
    delayMs: 340,
    sparks: [
      { x: 0, y: -34, color: "#fff2b5" },
      { x: 24, y: -22, color: "#ffd76c" },
      { x: 31, y: 0, color: "#fff9df" },
      { x: 22, y: 22, color: "#edb14f" },
      { x: 0, y: 32, color: "#ffe08a" },
      { x: -23, y: 22, color: "#fff4c8" },
      { x: -31, y: 0, color: "#f1bd62" },
      { x: -24, y: -22, color: "#fff7d5" },
    ],
  },
]);

function renderWinnerFireworks({
  seat,
  burstElapsedMs = 0,
  reducedMotion = false,
}) {
  return `
    <div
      class="seat-winner-fireworks ${reducedMotion ? "reduced-motion" : ""}"
      data-winner-fireworks-seat="${seat}"
      aria-hidden="true"
    >
      ${winnerFireworkBursts
        .map(
          (burst) => `
          <span
            class="seat-firework-cluster seat-firework-cluster-${burst.key}"
            style="left:${burst.left}; top:${burst.top};"
          >
            <span
              class="seat-firework-bloom"
              style="animation-delay:${burst.delayMs - burstElapsedMs}ms;"
            ></span>
            ${burst.sparks
              .map(
                (spark, index) => `
                  <span
                    class="seat-firework-spark"
                    style="
                      --winner-spark-x:${spark.x}px;
                      --winner-spark-y:${spark.y}px;
                      --winner-spark-color:${spark.color};
                      animation-delay:${burst.delayMs + index * 28 - burstElapsedMs}ms;
                    "
                  ></span>
                `,
              )
              .join("")}
          </span>
        `,
        )
        .join("")}
    </div>
  `;
}

function renderSeat({
  snapshot,
  player,
  localSeat,
  animations,
  turnArrivalSeat,
  presenceNow,
  kickSeatArmed,
  visibleShoutoutsBySeat,
  savedShoutoutsBySeat,
  winnerCelebration,
}) {
  const isCurrentTurn = player.seat === snapshot.current_turn_seat;
  const isWinner = Boolean(
    snapshot.status === "GAME_OVER" &&
      winnerCelebration?.winnerSeats?.includes(player.seat),
  );
  const showWinnerBurst = Boolean(
    isWinner &&
      winnerCelebration?.burstWinnerSeats?.includes(player.seat) &&
      winnerCelebration?.burstDurationMs > 0,
  );
  const isYou = player.seat === localSeat;
  const placementBadge = placementBadgeForPlayer(snapshot, player);
  const seatClasses = [
    "seat-panel",
    seatPositionClass(snapshot, localSeat, player),
    isCurrentTurn ? "current-turn" : "",
    turnArrivalSeat === player.seat ? "turn-arrival" : "",
    isWinner ? "winner" : "",
    showWinnerBurst ? "winner-bursting" : "",
    isYou ? "you" : "",
    seatHasActiveMotion(animations, player.seat, ["deal"])
      ? "motion-deal-target"
      : "",
    seatHasActiveMotion(animations, player.seat, ["lock"])
      ? "motion-lock-target"
      : "",
    seatHasActiveMotion(animations, player.seat, ["take-pile"])
      ? "motion-take-target"
      : "",
    seatHasActiveMotion(animations, player.seat, ["reveal-hidden"])
      ? "motion-reveal-target"
      : "",
    !player.is_connected ? "disconnected" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const seatBadges = [
    placementBadge
      ? `<span class="seat-badge ${placementBadge.classes.join(" ")}">${escapeHtml(placementBadge.label)}</span>`
      : "",
    isYou ? '<span class="seat-badge seat-badge-meta">You</span>' : "",
    player.is_host ? '<span class="seat-badge seat-badge-meta">Host</span>' : "",
    !player.is_connected
      ? '<span class="seat-badge seat-badge-meta">Offline</span>'
      : "",
  ]
    .filter(Boolean)
    .join("");

  return `
    <div class="${seatClasses}" data-motion-anchor="seat-seat-${player.seat}">
      ${
        isWinner
          ? `
        <div class="seat-winner-surface" aria-hidden="true">
          <span class="seat-winner-glow"></span>
          <span class="seat-winner-shimmer"></span>
        </div>
      `
          : ""
      }
      ${
        showWinnerBurst
          ? renderWinnerFireworks({
              seat: player.seat,
              burstElapsedMs: winnerCelebration.burstElapsedMs,
              reducedMotion: winnerCelebration.reducedMotion,
            })
          : ""
      }
      <div class="seat-badge-rail">
        ${seatBadges}
        <span
          class="seat-badge-replay-region"
          data-shoutout-badge-seat="${player.seat}"
        >
          ${renderSeatShoutoutReplayBadge({
            seat: player.seat,
            shoutout: savedShoutoutsBySeat?.[player.seat] || null,
          })}
        </span>
      </div>
      <div class="seat-panel-body">
      <div class="seat-header">
        <div class="seat-title-row">
          <strong>${escapeHtml(player.display_name)}</strong>
        </div>
      </div>
      ${renderOfflinePresence({
        player,
        snapshot,
        localSeat,
        presenceNow,
        kickSeatArmed,
      })}
      <div class="seat-shoutout-region" data-shoutout-seat="${player.seat}">
        ${renderSeatShoutouts({
          snapshot,
          player,
          localSeat,
          shoutouts: visibleShoutoutsBySeat?.[player.seat] || [],
        })}
      </div>
      <div class="seat-hand-row" data-motion-anchor="seat-hand-${player.seat}">${renderSeatHandFan(player.private_cards_count)}</div>
      <div
        class="seat-public-cards"
        data-motion-anchor="seat-public-${player.seat}"
      >
        <div class="seat-public-anchor" data-motion-anchor="seat-hidden-${player.seat}">
          ${renderSeatPublicStack(player.public_cards, player.hidden_cards_count)}
        </div>
      </div>
      </div>
    </div>
  `;
}

function renderMiniCard(card, attributes = "") {
  const highLowArrow =
    card.high_low_choice === "HIGHER"
      ? "\u25B2"
      : card.high_low_choice === "LOWER"
        ? "\u25BC"
        : "";
  const rankMarkup = isJokerCard(card) ? jokerSymbol : rankLabel(card.rank);
  return `
    <div class="mini-card ${isRedSuit(card.suit) ? "red" : ""} ${isJokerCard(card) ? "joker" : ""}" ${attributes}>
      <span class="mini-card-rank-line">${rankMarkup}${highLowArrow ? `<span class="mini-card-arrow" aria-hidden="true">${highLowArrow}</span>` : ""}</span>
      <span>${isJokerCard(card) ? (card.effective_rank ? `as ${rankLabel(card.effective_rank)}` : "wild") : suitLabel(card.suit)}</span>
    </div>
  `;
}

function renderPilePreview(playPile) {
  if (playPile.length === 0) {
    return "";
  }
  const visibleCards = playPile.slice(0, playPilePreviewLimit).reverse();
  return visibleCards
    .map((card, index) =>
      renderMiniCard(
        card,
        index === visibleCards.length - 1 ? 'data-motion-rect="pile-top"' : "",
      ),
    )
    .join("");
}

function renderDeckPreview(cardsInDeck) {
  const visibleCards = Math.min(cardsInDeck, 3);
  return `
    ${Array.from(
      { length: visibleCards },
      (_, index) => `
      <span
        class="deck-back-card"
        ${index === visibleCards - 1 ? 'data-motion-rect="deck-top"' : ""}
        style="transform: translate(${index * 4}px, ${index * 3}px) rotate(${index * 3 - 3}deg);"
      ></span>
    `,
    ).join("")}
    <span class="deck-count-badge">${cardsInDeck}</span>
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

function shouldShowStatusMessage(message) {
  return message && !/^7 or (higher|lower)!$/.test(message);
}

function displayedDeckCount(snapshot) {
  if (snapshot.status === "LOBBY") {
    return 54;
  }
  return snapshot.cards_in_deck;
}

export function deriveTableLayoutVariant({
  viewportWidth = 390,
  viewportHeight = 844,
}) {
  const aspectRatio = viewportWidth / Math.max(viewportHeight, 1);
  if (aspectRatio < 0.52) {
    return "tall";
  }
  if (aspectRatio > 0.68) {
    return "wide";
  }
  return "balanced";
}

export function deriveHandLayout({
  cardCount,
  playerCount,
  viewportWidth = 390,
  viewportHeight = 844,
}) {
  const compactViewport =
    viewportHeight < 760 || playerCount >= 4 || viewportWidth < 420;
  const narrowViewport = viewportWidth < 400;
  const availableWidth = Math.max(viewportWidth - 64, 220);
  const maxWidth = compactViewport ? 46 : 72;
  const minWidth = compactViewport ? 36 : 46;
  const stepFactor = cardCount >= 7 ? 0.48 : cardCount >= 5 ? 0.54 : 0.62;
  const fitWidth =
    cardCount <= 1
      ? maxWidth
      : Math.floor(
          availableWidth / (1 + Math.max(0, cardCount - 1) * stepFactor),
        );
  const shouldScroll =
    cardCount > 0 &&
    (fitWidth < minWidth ||
      (compactViewport && cardCount >= 5) ||
      (narrowViewport && cardCount >= 4));
  const cardWidth = shouldScroll
    ? narrowViewport
      ? 35
      : 64
    : Math.max(minWidth, Math.min(maxWidth, fitWidth || maxWidth));
  const overlap = Math.round(
    cardWidth * (shouldScroll ? (narrowViewport ? 0.26 : 0.1) : 1 - stepFactor),
  );
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

function renderTurnToast(turnNotice) {
  if (!turnNotice.visible) {
    return "";
  }

  return `
    <div class="turn-toast" aria-live="polite">
      <strong>${escapeHtml(turnNotice.headline)}</strong>
      <span>${escapeHtml(turnNotice.copy)}</span>
    </div>
  `;
}

function renderPileAction(gameplayUi) {
  if (!gameplayUi.actionPanel.showTakePileAction) {
    return "";
  }

  return `
    <button class="button accent pile-action" id="take-pile-overlay">
      Take pile
    </button>
  `;
}

export function renderRulesMenuView({ open, optionalTakePileEnabled }) {
  if (!open) {
    return "";
  }

  const optionalTakeRuleCopy = optionalTakePileEnabled
    ? " This table also allows taking the pile voluntarily at the start of your turn."
    : " Some lobbies may enable taking the pile voluntarily at the start of a turn.";

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
            <p>Play one or more cards of the same rank. If you cannot play, you take the whole play pile. Once your hand is empty, you use public cards, then reveal hidden cards one by one onto the pile.${optionalTakeRuleCopy}</p>
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

export function renderShoutoutMenuView({
  open = false,
  canSendShoutouts = false,
  onCooldown = false,
  presets = [],
  composer = null,
} = {}) {
  if (!open || !canSendShoutouts || onCooldown) {
    return "";
  }

  const composerState = composer || {
    open: false,
    text: "",
    emoji: "",
    error: "",
    maxTextLength: 50,
    emojiOptions: [],
  };

  return `
    <div class="shoutout-menu-layer">
      <button
        class="shoutout-menu-backdrop"
        id="close-shoutout-menu-backdrop"
        type="button"
        aria-label="Close shoutout menu"
      ></button>
      <section class="shoutout-menu" aria-label="Table shoutouts">
        <div class="shoutout-menu-header">
          <div>
            <p class="section-title">Shoutouts</p>
          </div>
          <button class="button secondary button-inline" id="close-shoutout-menu" type="button">Close</button>
        </div>
        ${
          composerState.open
            ? `
          <form class="shoutout-composer" data-mode="custom-shoutout">
            <div class="shoutout-composer-header">
              <p class="shoutout-composer-title">Custom</p>
              <button class="button secondary button-inline" id="close-custom-shoutout" type="button">Back</button>
            </div>
            <label class="shoutout-composer-field" for="custom-shoutout-text">
              <span class="shoutout-composer-label">Message</span>
              <input
                id="custom-shoutout-text"
                class="text-input shoutout-composer-input"
                type="text"
                maxlength="${Math.max(1, composerState.maxTextLength || 50)}"
                placeholder="Short and sharp"
                value="${escapeHtml(composerState.text || "")}"
                autocomplete="off"
                autocapitalize="sentences"
                spellcheck="false"
              />
            </label>
            <div class="shoutout-composer-copy">Up to ${Math.max(1, composerState.maxTextLength || 50)} characters. Emoji optional.</div>
            <div class="shoutout-emoji-picker" role="group" aria-label="Choose one emoji">
              ${(composerState.emojiOptions || [])
                .map(
                  (option) => `
                <button
                  class="shoutout-emoji-option ${composerState.emoji === option.value ? "selected" : ""}"
                  type="button"
                  data-shoutout-emoji="${escapeHtml(option.value)}"
                  title="${escapeHtml(option.label)}"
                  aria-pressed="${composerState.emoji === option.value ? "true" : "false"}"
                >${escapeHtml(option.value)}</button>
              `,
                )
                .join("")}
            </div>
            ${
              composerState.error
                ? `<div class="shoutout-composer-error">${escapeHtml(composerState.error)}</div>`
                : ""
            }
            <div class="shoutout-composer-actions">
              <button class="button accent" type="submit">Send</button>
            </div>
          </form>
        `
            : `
          <div class="shoutout-grid">
            <button
              class="shoutout-chip shoutout-chip-custom"
              id="open-custom-shoutout"
              type="button"
              title="Custom"
              style="--shoutout-accent:#d85b32;"
            >
              <span class="shoutout-chip-emoji">+</span>
              <span class="shoutout-chip-label">Custom</span>
            </button>
            ${presets
              .map(
                (preset) => `
              <button
                class="shoutout-chip"
                type="button"
                data-shoutout-key="${escapeHtml(preset.key)}"
                style="--shoutout-accent:${escapeHtml(preset.color)};"
                title="${escapeHtml(preset.label)}"
              >
                <span class="shoutout-chip-emoji">${escapeHtml(preset.emoji)}</span>
                <span class="shoutout-chip-label">${escapeHtml(preset.label)}</span>
              </button>
            `,
              )
              .join("")}
          </div>
        `
        }
      </section>
    </div>
  `;
}

function renderLobbySettings(snapshot, isHost) {
  const enabled = snapshot.rules.allow_optional_take_pile;
  return `
    <div class="lobby-setting-card" data-lobby-setting="optional-take-pile">
      <div class="lobby-setting-copy">
        <strong>Optional take pile</strong>
        <span>${isHost ? "Allow taking the pile at the start of a turn." : "Host controls whether players may take the pile voluntarily."}</span>
      </div>
      ${
        isHost
          ? `
        <button
          class="toggle-switch-button ${enabled ? "active" : ""}"
          id="toggle-optional-take-pile"
          type="button"
          role="switch"
          aria-checked="${enabled ? "true" : "false"}"
          aria-label="Toggle optional take pile"
        >
          <span class="toggle-switch-track" aria-hidden="true">
            <span class="toggle-switch-knob"></span>
          </span>
        </button>
      `
          : `
        <div class="lobby-setting-indicator ${enabled ? "active" : ""}" aria-label="Optional take pile is ${enabled ? "on" : "off"}">
          ${enabled ? "On" : "Off"}
        </div>
      `
      }
    </div>
  `;
}

function renderActions({ gameplayUi, viewState }) {
  const selectedIds = new Set(viewState.selectedCardIds);
  const handPrimaryAction = gameplayUi.actionPanel.primaryHandAction;
  const localSeat = viewState.localSeat;
  const animations = viewState.animations;
  const showMobileTurnPrompt = gameplayUi.currentGameState === "DURING_GAME";
  const dockClasses = [
    "panel",
    "hand-dock",
    viewState.handLayout.classes,
    seatHasActiveMotion(animations, localSeat, ["deal"]) ? "motion-deal-target" : "",
    seatHasActiveMotion(animations, localSeat, ["lock"]) ? "motion-lock-target" : "",
    seatHasActiveMotion(animations, localSeat, ["play"]) ? "motion-play-target" : "",
    hasActiveMotion(animations, "draw-self") ? "motion-draw-target" : "",
    seatHasActiveMotion(animations, localSeat, ["take-pile"])
      ? "motion-take-target"
      : "",
    viewState.turnArrivalSeat === localSeat ? "turn-arrival" : "",
    gameplayUi.currentGameState === "DURING_GAME" && !gameplayUi.isMyTurn
      ? "waiting"
      : "",
  ]
    .filter(Boolean)
    .join(" ");

  return `
    <section class="${dockClasses}" style="${viewState.handLayout.style}">
      <div class="dock-header">
        <div class="dock-header-main">
          <p class="section-title">Your hand</p>
        </div>
        ${
          handPrimaryAction
            ? `
          <button
            class="button accent button-inline dock-header-action"
            id="hand-primary-action"
            data-primary-action="${handPrimaryAction.id}"
            ${handPrimaryAction.disabled ? "disabled" : ""}
          >${handPrimaryAction.label}</button>
        `
            : ""
        }
      </div>
      <div class="dock-prompt">${escapeHtml(gameplayUi.turnGuidance.prompt)}</div>
      ${viewState.errorMessage ? `<div class="dock-error">${escapeHtml(viewState.errorMessage)}</div>` : ""}
      ${
        gameplayUi.pendingJoker.active
          ? `
        <div class="joker-pending-card">
          ${renderCard(gameplayUi.pendingJoker.card, false, false)}
        </div>
      `
          : `
        <div class="hand-fan" data-motion-anchor="hand-self">
          ${
            gameplayUi.privateCards
              .map((card) =>
                renderCard(
                  card,
                  selectedIds.has(cardId(card)),
                  true,
                  viewState.hiddenLocalHandCardIds.includes(cardId(card)),
                ),
              )
              .join("") || '<p class="muted">No cards in hand right now.</p>'
          }
        </div>
      `
      }
      <div class="actions">
        ${
          gameplayUi.actionPanel.showJokerChoiceUi
            ? `
          <div class="choice-block">
            <strong class="choice-title">${gameplayUi.pendingJoker.isRevealedJoker ? "Choose the revealed joker" : "Choose the joker rank"}</strong>
            <div class="joker-choice-row">
              ${gameplayUi.selectedPlay.jokerChoices
                .map(
                  (rank) => `
                <button
                  class="button ${viewState.jokerRank === rank ? "accent" : "secondary"}"
                  data-joker-rank="${rank}"
                >${rankLabel(rank)}</button>
              `,
                )
                .join("")}
            </div>
          </div>
        `
            : ""
        }
        ${
          gameplayUi.actionPanel.showHighLowChoiceUi
            ? `
          <div class="choice-block">
            <div class="choice-row">
              <button class="button ${viewState.highLowChoice === "LOWER" ? "accent" : "secondary"}" id="choose-lower">7 or lower</button>
              <button class="button ${viewState.highLowChoice === "HIGHER" ? "accent" : "secondary"}" id="choose-higher">7 or higher</button>
            </div>
          </div>
        `
            : ""
        }
        ${
          gameplayUi.actionPanel.waitingText && !showMobileTurnPrompt
            ? `<p class="muted tiny">${escapeHtml(gameplayUi.actionPanel.waitingText)}</p>`
            : ""
        }
      </div>
    </section>
  `;
}

function renderTable({ snapshot, gameplayUi, viewState }) {
  const localPlayer = playerForSeat(snapshot, viewState.localSeat);
  const isHost = Boolean(localPlayer?.is_host);
  const showLobbyControls = snapshot.status === "LOBBY";
  const showShoutoutControls =
    snapshot.status === "LOBBY" ||
    snapshot.status === "IN_GAME" ||
    snapshot.status === "GAME_OVER";
  const showMobileLobbyLayout = snapshot.status === "LOBBY";
  const sortedPlayers = [...snapshot.players].sort(
    (left, right) =>
      relativeSeatIndex(snapshot, viewState.localSeat, left) -
      relativeSeatIndex(snapshot, viewState.localSeat, right),
  );

  const lobbyControls = showLobbyControls
    ? `
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
  `
    : "";

  const pilePreviewClasses = [
    "pile-preview",
    hasActiveMotion(viewState.animations, "play") ||
    hasActiveMotion(viewState.animations, "reveal-hidden")
      ? "settling"
      : "",
    hasActiveMotion(viewState.animations, "take-pile") ? "taking" : "",
    hasActiveMotion(viewState.animations, "burn") ? "burning" : "",
  ]
    .filter(Boolean)
    .join(" ");
  const deckStackClasses = [
    "deck-stack",
    hasActiveMotion(viewState.animations, "deal") ? "dealing" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return `
    <section class="panel table-stage stack">
      ${showMobileLobbyLayout && viewState.errorMessage ? `<div class="dock-error">${escapeHtml(viewState.errorMessage)}</div>` : ""}
      <div class="table-map">
        ${
          showMobileLobbyLayout
            ? `
          <div class="table-map-controls">
            ${lobbyControls}
          </div>
        `
            : ""
        }
        <div class="table-surface"></div>
        ${sortedPlayers
          .map((player) =>
            renderSeat({
              snapshot,
              player,
              localSeat: viewState.localSeat,
              animations: viewState.animations,
              turnArrivalSeat: viewState.turnArrivalSeat,
              presenceNow: viewState.presenceNow,
              kickSeatArmed: viewState.kickSeatArmed,
              visibleShoutoutsBySeat: viewState.visibleShoutoutsBySeat,
              savedShoutoutsBySeat: viewState.savedShoutoutsBySeat,
              winnerCelebration: viewState.winnerCelebration,
            }),
          )
          .join("")}
        ${renderTurnToast(viewState.turnNotice)}
        <div class="table-center">
          ${snapshot.status === "LOBBY" ? renderLobbySettings(snapshot, isHost) : ""}
          ${
            snapshot.status === "LOBBY" && !isHost
              ? `
            <div class="event-box">
              <span>Waiting for host to start the game.</span>
            </div>
          `
              : ""
          }
          ${
            shouldShowStatusMessage(snapshot.status_message)
              ? `
            <div class="event-box">
              <span>${escapeHtml(snapshot.status_message)}</span>
            </div>
          `
              : ""
          }
          ${
            snapshot.status === "GAME_OVER" && isHost
              ? `
            <div class="primary-action-row">
              <button class="button full-width" id="rematch-game" type="button">Rematch</button>
            </div>
          `
              : ""
          }
          <div class="table-resources">
            <div class="deck-orb">
              <span class="resource-label">Deck</span>
              <div class="${deckStackClasses}" data-motion-anchor="deck">
                ${renderDeckPreview(displayedDeckCount(snapshot))}
              </div>
            </div>
            <div class="pile-zone">
              <span class="resource-label">Play pile</span>
              <div class="${pilePreviewClasses}" data-motion-anchor="pile">${renderPilePreview(snapshot.play_pile)}</div>
              <span class="pile-caption">${playPileCaption(snapshot.play_pile)}</span>
              ${renderPileAction(gameplayUi)}
            </div>
          </div>
        </div>
        ${
          showShoutoutControls
            ? `
          <button
            class="table-shoutout-trigger ${viewState.shoutoutTrigger.shoutoutEnabled ? "" : "disabled"} ${viewState.shoutoutTrigger.shoutoutLocked ? "locked" : ""}"
            id="open-shoutout-menu"
            type="button"
            aria-label="Open shoutouts"
            title="${
              !viewState.shoutoutTrigger.shoutoutReady
                ? "Connecting to the table"
                : viewState.shoutoutTrigger.shoutoutLocked
                  ? `Shoutouts available in ${Math.max(
                      1,
                      Math.ceil(viewState.shoutoutTrigger.shoutoutCooldown.remainingMs / 1000),
                    )}s`
                  : "Shoutouts"
            }"
            style="${viewState.shoutoutTrigger.shoutoutFillStyle};"
            ${viewState.shoutoutTrigger.shoutoutEnabled ? "" : "disabled"}
          >
            <span class="shoutout-trigger-fill" aria-hidden="true"></span>
            <span class="shoutout-joker-emoji" aria-hidden="true">${jokerSymbol}</span>
          </button>
        `
            : ""
        }
        <button class="table-help-trigger" id="open-rules-menu" type="button" aria-label="Open rules" title="Rules">?</button>
        ${renderRulesMenuView(viewState.rulesMenu)}
        <div class="table-shoutout-menu-region" data-shoutout-menu-region>
          ${renderShoutoutMenuView(viewState.shoutoutMenu)}
        </div>
      </div>
      ${
        snapshot.status === "LOBBY" && isHost
          ? `
        <div class="primary-action-row">
          <button class="button accent full-width" id="start-game" ${snapshot.players.length < 2 ? "disabled" : ""}>Start game</button>
        </div>
      `
          : ""
      }
    </section>
  `;
}

export function renderGameplayScreenView({ snapshot, gameplayUi, viewState }) {
  const localPlayer = playerForSeat(snapshot, viewState.localSeat);
  const localPlayerFinished = Boolean(localPlayer?.finished_position != null);
  const showMobileLobbyLayout = snapshot.status === "LOBBY";
  const gameScreenClasses = [
    "game-screen",
    `players-${snapshot.players.length}`,
    "mobile-one-screen",
    `layout-${viewState.tableLayoutVariant}`,
    snapshot.status === "GAME_OVER" ? "game-over-screen" : "",
    localPlayerFinished ? "local-player-finished" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return {
    gameScreenClasses,
    tableHtml: renderTable({ snapshot, gameplayUi, viewState }),
    actionsHtml:
      showMobileLobbyLayout || localPlayerFinished
        ? ""
        : renderActions({ gameplayUi, viewState }),
  };
}

export function syncGameplayShoutoutView({
  root = document,
  snapshot,
  viewState,
}) {
  if (!root || !snapshot || !viewState) {
    return;
  }

  const menuRegion = root.querySelector("[data-shoutout-menu-region]");
  if (menuRegion) {
    const nextMarkup = renderShoutoutMenuView(viewState.shoutoutMenu);
    const nextSignature = JSON.stringify({
      open: Boolean(viewState.shoutoutMenu?.open),
      canSendShoutouts: Boolean(viewState.shoutoutMenu?.canSendShoutouts),
      onCooldown: Boolean(viewState.shoutoutMenu?.onCooldown),
      presets: (viewState.shoutoutMenu?.presets || []).map((preset) => preset.key),
      composerOpen: Boolean(viewState.shoutoutMenu?.composer?.open),
      composerEmoji: viewState.shoutoutMenu?.composer?.emoji || "",
      composerText: viewState.shoutoutMenu?.composer?.text || "",
      composerError: viewState.shoutoutMenu?.composer?.error || "",
    });
    if (menuRegion.dataset.shoutoutMenuSignature !== nextSignature) {
      menuRegion.innerHTML = nextMarkup;
      menuRegion.dataset.shoutoutMenuSignature = nextSignature;
    }
  }

  root.querySelectorAll("[data-shoutout-seat]").forEach((region) => {
    const seat = Number(region.getAttribute("data-shoutout-seat"));
    const shoutouts = viewState.visibleShoutoutsBySeat?.[seat] || [];
    const player = playerForSeat(snapshot, seat);
    const nextMarkup = player
      ? renderSeatShoutouts({
          snapshot,
          player,
          localSeat: viewState.localSeat,
          shoutouts,
        })
      : "";
    const nextSignature = shoutouts
      .map(
        (shoutout) =>
          `${shoutout.id}:${shoutout.expiresAt}:${shoutout.text}:${shoutout.emoji || ""}`,
      )
      .join("|");
    if (region.dataset.shoutoutSignature !== nextSignature) {
      region.innerHTML = nextMarkup;
      region.dataset.shoutoutSignature = nextSignature;
    }
  });

  root.querySelectorAll("[data-shoutout-badge-seat]").forEach((region) => {
    const seat = Number(region.getAttribute("data-shoutout-badge-seat"));
    const shoutout = viewState.savedShoutoutsBySeat?.[seat] || null;
    const nextMarkup = renderSeatShoutoutReplayBadge({
      seat,
      shoutout,
    });
    const nextSignature = shoutout
      ? `${shoutout.id}:${shoutout.text}:${shoutout.emoji || ""}`
      : "";
    if (region.dataset.shoutoutBadgeSignature !== nextSignature) {
      region.innerHTML = nextMarkup;
      region.dataset.shoutoutBadgeSignature = nextSignature;
    }
  });
}
