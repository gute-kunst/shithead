const storageKey = "shithead.alpha.session";
const playPilePreviewLimit = 6;
const jokerRank = 15;
const jokerAllowedRanks = [3, 4, 6, 7, 8, 9, 11, 13, 12, 14];
const jokerSymbol = "★";
const shoutoutCooldownMs = 4000;
const cardTapSuppressMs = 350;
const handDragThreshold = 14;
const mouseDragInputId = -1;

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
  kickSeatArmed: null,
  kickSeatConfirmTimer: null,
  presenceTicker: null,
  presenceNow: Date.now(),
  shoutoutUnlockTimer: null,
  rulesMenuOpen: false,
  shoutoutMenuOpen: false,
  animations: [],
  localMotionAnimations: [],
  animationCounter: 0,
  animationTimers: [],
  turnArrivalSeat: null,
  turnArrivalTimer: null,
  motionAnchors: {},
  motionAnchorSignature: "",
  motionRerenderScheduled: false,
  pendingLocalPlay: null,
  pendingLocalDrawAnimation: null,
  hiddenLocalHandCardIds: [],
  localPlaySendTimer: null,
  handFanScrollLeft: 0,
  seenShoutoutEvents: [],
  handDragActiveInputId: null,
  handDragStartX: 0,
  handDragStartY: 0,
  handDragStartScrollLeft: 0,
  handDragDragging: false,
  handDragQueuedRender: false,
  handTouchActiveId: null,
  handTouchStartX: 0,
  handTouchStartY: 0,
  handTouchStartScrollLeft: 0,
  handTouchStartAt: 0,
  handTouchMoved: false,
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

function clearKickSeatConfirmTimer() {
  if (state.kickSeatConfirmTimer !== null) {
    window.clearTimeout(state.kickSeatConfirmTimer);
    state.kickSeatConfirmTimer = null;
  }
}

function clearPresenceTicker() {
  if (state.presenceTicker !== null) {
    window.clearInterval(state.presenceTicker);
    state.presenceTicker = null;
  }
}

function clearShoutoutUnlockTimer() {
  if (state.shoutoutUnlockTimer !== null) {
    window.clearTimeout(state.shoutoutUnlockTimer);
    state.shoutoutUnlockTimer = null;
  }
}

function pruneSeenShoutoutEvents(now = Date.now()) {
  state.seenShoutoutEvents = state.seenShoutoutEvents.filter(
    (entry) => now - entry.seenAt <= shoutoutCooldownMs * 3,
  );
}

function rememberShoutoutEvent(eventId) {
  if (!eventId) {
    return true;
  }
  const now = Date.now();
  pruneSeenShoutoutEvents(now);
  if (state.seenShoutoutEvents.some((entry) => entry.eventId === eventId)) {
    return false;
  }
  state.seenShoutoutEvents = [
    ...state.seenShoutoutEvents,
    { eventId, seenAt: now },
  ].slice(-24);
  return true;
}

function clearHandFanDraggingClasses() {
  app.querySelectorAll(".hand-fan.is-dragging").forEach((element) => {
    element.classList.remove("is-dragging");
  });
}

function resetHandFanTouchState() {
  state.handTouchActiveId = null;
  state.handTouchStartX = 0;
  state.handTouchStartY = 0;
  state.handTouchStartScrollLeft = 0;
  state.handTouchStartAt = 0;
  state.handTouchMoved = false;
}

function resetHandFanDragState() {
  state.handDragActiveInputId = null;
  state.handDragStartX = 0;
  state.handDragStartY = 0;
  state.handDragStartScrollLeft = 0;
  state.handDragDragging = false;
  state.handDragQueuedRender = false;
  resetHandFanTouchState();
  clearHandFanDraggingClasses();
}

function isHandDragActive() {
  return state.handDragActiveInputId !== null;
}

function isHandInteractionActive() {
  return isHandDragActive() || state.handTouchActiveId !== null;
}

function suppressCardTap() {
  state.suppressCardTapUntil = Date.now() + cardTapSuppressMs;
}

function beginHandFanTouch(inputId, x, y, handFan) {
  state.handTouchActiveId = inputId;
  state.handTouchStartX = x;
  state.handTouchStartY = y;
  state.handTouchStartScrollLeft = handFan.scrollLeft;
  state.handTouchStartAt = Date.now();
  state.handTouchMoved = false;
}

function updateHandFanTouch(inputId, x, y, handFan) {
  if (state.handTouchActiveId !== inputId) {
    return;
  }
  state.handFanScrollLeft = handFan.scrollLeft;
  const deltaX = Math.abs(x - state.handTouchStartX);
  const deltaY = Math.abs(y - state.handTouchStartY);
  const scrollDelta = Math.abs(handFan.scrollLeft - state.handTouchStartScrollLeft);
  if (
    deltaX >= handDragThreshold ||
    deltaY >= handDragThreshold ||
    scrollDelta >= Math.max(6, handDragThreshold / 2)
  ) {
    state.handTouchMoved = true;
  }
}

function finishHandFanTouch(inputId, handFan = app.querySelector(".hand-fan")) {
  if (state.handTouchActiveId !== inputId) {
    return;
  }
  const touchDuration = Date.now() - state.handTouchStartAt;
  const currentScrollLeft = handFan ? handFan.scrollLeft : state.handFanScrollLeft;
  state.handFanScrollLeft = currentScrollLeft;
  const scrollDelta = Math.abs(currentScrollLeft - state.handTouchStartScrollLeft);
  if (
    state.handTouchMoved ||
    scrollDelta >= Math.max(6, handDragThreshold / 2) ||
    (scrollDelta > 0 && touchDuration > cardTapSuppressMs)
  ) {
    suppressCardTap();
  }
  resetHandFanTouchState();

  const queuedRender = state.handDragQueuedRender;
  state.handDragQueuedRender = false;
  if (queuedRender) {
    render({ force: true });
  }
}

function beginHandFanDrag(inputId, x, y, handFan) {
  state.handDragActiveInputId = inputId;
  state.handDragStartX = x;
  state.handDragStartY = y;
  state.handDragStartScrollLeft = handFan.scrollLeft;
  state.handDragDragging = false;
  handFan.classList.remove("is-dragging");
}

function updateHandFanDrag(inputId, x, y, handFan) {
  if (state.handDragActiveInputId !== inputId) {
    return false;
  }

  const deltaX = x - state.handDragStartX;
  const deltaY = y - state.handDragStartY;
  if (!state.handDragDragging) {
    if (
      Math.abs(deltaX) < handDragThreshold ||
      Math.abs(deltaX) <= Math.abs(deltaY)
    ) {
      return false;
    }
    state.handDragDragging = true;
    handFan.classList.add("is-dragging");
    try {
      handFan.setPointerCapture(inputId);
    } catch (error) {}
  }

  handFan.scrollLeft = state.handDragStartScrollLeft - deltaX;
  state.handFanScrollLeft = handFan.scrollLeft;
  suppressCardTap();
  return true;
}

function finishHandFanDrag(inputId, handFan = app.querySelector(".hand-fan")) {
  if (state.handDragActiveInputId !== inputId) {
    return;
  }

  if (state.handDragDragging) {
    suppressCardTap();
  }

  state.handDragActiveInputId = null;
  state.handDragStartX = 0;
  state.handDragStartY = 0;
  state.handDragStartScrollLeft = 0;
  state.handDragDragging = false;
  if (handFan) {
    handFan.classList.remove("is-dragging");
  }
  clearHandFanDraggingClasses();

  const queuedRender = state.handDragQueuedRender;
  state.handDragQueuedRender = false;
  if (queuedRender) {
    render({ force: true });
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

function resetKickSeatConfirmation({ rerender = false } = {}) {
  clearKickSeatConfirmTimer();
  state.kickSeatArmed = null;
  if (rerender) {
    render();
  }
}

function armKickSeatConfirmation(seat) {
  clearKickSeatConfirmTimer();
  state.kickSeatArmed = seat;
  state.kickSeatConfirmTimer = window.setTimeout(() => {
    state.kickSeatConfirmTimer = null;
    state.kickSeatArmed = null;
    render();
  }, 3000);
}

function handleKickSeatClick(seat) {
  if (state.kickSeatArmed === seat) {
    kickPlayer(seat);
    return;
  }
  armKickSeatConfirmation(seat);
  render();
}

function openRulesMenu() {
  state.shoutoutMenuOpen = false;
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

function openShoutoutMenu() {
  if (isShoutoutOnCooldown()) {
    state.shoutoutMenuOpen = false;
    render();
    return;
  }
  state.rulesMenuOpen = false;
  state.shoutoutMenuOpen = true;
  render();
}

function closeShoutoutMenu() {
  if (!state.shoutoutMenuOpen) {
    return;
  }
  state.shoutoutMenuOpen = false;
  render();
}

function toggleShoutoutMenu() {
  if (state.shoutoutMenuOpen) {
    closeShoutoutMenu();
    return;
  }
  openShoutoutMenu();
}

function clearTurnNoticeTimer() {
  if (state.turnNoticeTimer !== null) {
    window.clearTimeout(state.turnNoticeTimer);
    state.turnNoticeTimer = null;
  }
}

function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function clearAnimationTimers() {
  state.animationTimers.forEach((timer) => window.clearTimeout(timer));
  state.animationTimers = [];
}

function clearTurnArrivalTimer() {
  if (state.turnArrivalTimer !== null) {
    window.clearTimeout(state.turnArrivalTimer);
    state.turnArrivalTimer = null;
  }
}

function clearLocalPlaySendTimer() {
  if (state.localPlaySendTimer !== null) {
    window.clearTimeout(state.localPlaySendTimer);
    state.localPlaySendTimer = null;
  }
}

function clearPendingLocalPlay() {
  clearLocalPlaySendTimer();
  state.pendingLocalPlay = null;
  state.hiddenLocalHandCardIds = [];
}

function clearMotionState() {
  clearAnimationTimers();
  clearTurnArrivalTimer();
  clearLocalPlaySendTimer();
  state.animations = [];
  state.seenShoutoutEvents = [];
  state.localMotionAnimations = [];
  state.turnArrivalSeat = null;
  state.motionAnchors = {};
  state.motionAnchorSignature = "";
  state.motionRerenderScheduled = false;
  state.pendingLocalPlay = null;
  state.pendingLocalDrawAnimation = null;
  state.hiddenLocalHandCardIds = [];
  resetHandFanDragState();
}

function queueAnimation(animation) {
  const duration = prefersReducedMotion() ? 180 : animation.duration || 520;
  const id = state.animationCounter + 1;
  state.animationCounter = id;
  state.animations = [...state.animations, { ...animation, id, duration }];
  const timer = window.setTimeout(() => {
    state.animations = state.animations.filter((entry) => entry.id !== id);
    state.animationTimers = state.animationTimers.filter(
      (entry) => entry !== timer,
    );
    render();
  }, duration + 90);
  state.animationTimers = [...state.animationTimers, timer];
}

function queueLocalMotion(animation) {
  const duration = prefersReducedMotion() ? 180 : animation.duration || 540;
  const id = state.animationCounter + 1;
  state.animationCounter = id;
  state.localMotionAnimations = [
    ...state.localMotionAnimations,
    { ...animation, id, duration },
  ];
  const timer = window.setTimeout(() => {
    state.localMotionAnimations = state.localMotionAnimations.filter(
      (entry) => entry.id !== id,
    );
    state.animationTimers = state.animationTimers.filter(
      (entry) => entry !== timer,
    );
    render();
  }, duration + 120);
  state.animationTimers = [...state.animationTimers, timer];
}

function markTurnArrival(seat) {
  clearTurnArrivalTimer();
  state.turnArrivalSeat = seat;
  state.turnArrivalTimer = window.setTimeout(
    () => {
      state.turnArrivalTimer = null;
      state.turnArrivalSeat = null;
      document
        .querySelectorAll(".seat-panel.turn-arrival, .hand-dock.turn-arrival")
        .forEach((element) => {
          element.classList.remove("turn-arrival");
        });
    },
    prefersReducedMotion() ? 220 : 1100,
  );
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

function clearSession(errorMessage = "") {
  closeWebSocket();
  hideTurnNotice();
  clearRestoreRetryTimer();
  clearPresenceTicker();
  clearShoutoutUnlockTimer();
  clearMotionState();
  resetLeaveConfirmation();
  resetKickSeatConfirmation();
  state.rulesMenuOpen = false;
  state.shoutoutMenuOpen = false;
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
  render({ force: true });
}

function clearGameStateForLobby() {
  clearMotionState();
  clearPendingLocalPlay();
  resetSelection();
  state.privateState = null;
  state.error = "";
  state.handFanScrollLeft = 0;
  resetLeaveConfirmation();
  resetKickSeatConfirmation();
  state.rulesMenuOpen = false;
  state.shoutoutMenuOpen = false;
}

function forgetSavedSession() {
  closeWebSocket();
  hideTurnNotice();
  clearRestoreRetryTimer();
  clearPresenceTicker();
  clearShoutoutUnlockTimer();
  clearMotionState();
  resetLeaveConfirmation();
  resetKickSeatConfirmation();
  state.rulesMenuOpen = false;
  state.shoutoutMenuOpen = false;
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
  render({ force: true });
}

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

function collectAddedCards(
  previousCards = [],
  nextCards = [],
  limit = Infinity,
) {
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

function isJokerCard(card) {
  return Boolean(card && (card.is_joker || card.rank === jokerRank));
}

function cardEffectiveRank(card) {
  if (!card) {
    return null;
  }
  return isJokerCard(card) && Number.isInteger(card.effective_rank)
    ? card.effective_rank
    : card.rank;
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
  return (
    state.snapshot?.data?.players.find(
      (player) => player.seat === state.seat,
    ) || null
  );
}

function canHostRemovePlayer(player) {
  const self = me();
  return Boolean(
    self && self.is_host && !player.is_host && !player.is_connected,
  );
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

function renderOfflinePresence(player) {
  if (player.is_connected) {
    return "";
  }

  const lines = [];
  const nowMs = state.presenceNow || Date.now();
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
  } else if (canHostRemovePlayer(player)) {
    lines.push("Waiting for reconnect. Host can remove now.");
  } else {
    lines.push("Waiting for reconnect.");
  }

  const removeButton = canHostRemovePlayer(player)
    ? `
      <button
        class="button secondary button-inline seat-remove-button ${state.kickSeatArmed === player.seat ? "armed-remove" : ""}"
        type="button"
        data-kick-seat="${player.seat}"
        title="${state.kickSeatArmed === player.seat ? "Click again to remove" : "Remove offline player"}"
        aria-label="${state.kickSeatArmed === player.seat ? "Click again to remove" : "Remove offline player"}"
      >${state.kickSeatArmed === player.seat ? "Confirm remove" : "Remove"}</button>
    `
    : "";

  return `
    <div class="seat-presence">
      ${lines.map((line) => `<span class="seat-presence-line">${escapeHtml(line)}</span>`).join("")}
      ${removeButton ? `<div class="seat-actions">${removeButton}</div>` : ""}
    </div>
  `;
}

function syncPresenceTicker() {
  const snapshot = state.snapshot?.data;
  const hasOfflinePlayers = Boolean(
    snapshot?.players?.some((player) => !player.is_connected),
  );
  if (!hasOfflinePlayers) {
    clearPresenceTicker();
    return;
  }
  if (state.presenceTicker !== null) {
    return;
  }
  state.presenceTicker = window.setInterval(() => {
    state.presenceNow = Date.now();
    render();
  }, 1000);
}

function syncKickSeatConfirmation(snapshot = state.snapshot?.data) {
  if (!Number.isInteger(state.kickSeatArmed)) {
    return;
  }
  const armedPlayer = snapshot?.players?.find(
    (player) => player.seat === state.kickSeatArmed,
  );
  if (!armedPlayer || !canHostRemovePlayer(armedPlayer)) {
    resetKickSeatConfirmation();
  }
}

function winner() {
  return (
    state.snapshot?.data?.players.find(
      (player) => player.finished_position === 1,
    ) || null
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
    !hasPendingHiddenTake() &&
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

function hasPendingHiddenTake() {
  return Boolean(state.privateState?.data?.pending_hidden_take);
}

function optionalTakeRuleEnabled(snapshot = state.snapshot?.data) {
  return Boolean(snapshot?.rules?.allow_optional_take_pile);
}

function shoutoutPresets(snapshot = state.snapshot?.data) {
  return snapshot?.shoutout_presets || [];
}

function shoutoutCooldownState(privateState = state.privateState?.data) {
  const nextAvailableAt = privateState?.shoutout_next_available_at;
  if (!nextAvailableAt) {
    return null;
  }
  const dueAt = Date.parse(nextAvailableAt);
  if (!Number.isFinite(dueAt)) {
    return null;
  }
  const remainingMs = dueAt - Date.now();
  if (remainingMs <= 0) {
    return null;
  }
  const durationMs = shoutoutCooldownMs;
  const elapsedMs = Math.min(
    durationMs,
    Math.max(0, durationMs - remainingMs),
  );
  return {
    dueAt,
    durationMs,
    elapsedMs,
    remainingMs,
  };
}

function isShoutoutOnCooldown(privateState = state.privateState?.data) {
  return shoutoutCooldownState(privateState) !== null;
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

function syncShoutoutUnlockTimer() {
  clearShoutoutUnlockTimer();
  const cooldown = shoutoutCooldownState();
  if (!cooldown) {
    return;
  }
  state.shoutoutUnlockTimer = window.setTimeout(() => {
    state.shoutoutUnlockTimer = null;
    render();
  }, Math.max(0, cooldown.remainingMs) + 30);
}

function canSendShoutouts(snapshot = state.snapshot?.data) {
  return Boolean(
    snapshot &&
    state.wsReady &&
    (snapshot.status === "LOBBY" ||
      snapshot.status === "IN_GAME" ||
      snapshot.status === "GAME_OVER"),
  );
}

function canOptionallyTakePile(snapshot = state.snapshot?.data) {
  if (currentGameState() !== "DURING_GAME" || !isMyTurn()) {
    return false;
  }
  if (
    !optionalTakeRuleEnabled(snapshot) ||
    (snapshot?.play_pile?.length || 0) === 0
  ) {
    return false;
  }
  return !hasPendingJokerSelection() && !hasPendingHiddenTake();
}

function mustTakePile(snapshot = state.snapshot?.data) {
  if (currentGameState() !== "DURING_GAME" || !isMyTurn()) {
    return false;
  }
  if (hasPendingHiddenTake()) {
    return true;
  }
  return (
    privateCards().length > 0 &&
    !canPlayHiddenCard() &&
    !hasPlayablePrivateCard(snapshot)
  );
}

function privateCards() {
  return state.privateState?.data?.private_cards || [];
}

function currentHandScrollKey() {
  return privateCards()
    .map((card) => cardId(card))
    .join("|");
}

function restoreHandFanScroll() {
  const handFan = app.querySelector(".hand-fan");
  if (!handFan || state.handFanScrollLeft <= 0) {
    return;
  }
  const maxScrollLeft = Math.max(0, handFan.scrollWidth - handFan.clientWidth);
  handFan.scrollLeft = Math.min(
    maxScrollLeft,
    Math.max(0, state.handFanScrollLeft),
  );
}

function isLocalHandCardHidden(card) {
  return state.hiddenLocalHandCardIds.includes(cardId(card));
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
  const ranks = [
    ...new Set(
      state.selectedCards
        .filter((card) => !isJokerCard(card))
        .map((card) => card.rank),
    ),
  ];
  if (ranks.length !== 1) {
    return null;
  }
  return ranks[0];
}

function pendingJokerCard() {
  return state.privateState?.data?.pending_joker_card || null;
}

function hasPendingJokerSelection() {
  return Boolean(
    state.privateState?.data?.pending_joker_selection && pendingJokerCard(),
  );
}

function jokerOptions(
  snapshot = state.snapshot?.data,
  cards = state.selectedCards,
) {
  if (!cards.some((card) => isJokerCard(card))) {
    return [];
  }
  const validRanks = new Set(snapshot?.current_valid_ranks || []);
  const nonJokerRanks = [
    ...new Set(
      cards.filter((card) => !isJokerCard(card)).map((card) => card.rank),
    ),
  ];
  if (nonJokerRanks.length > 1) {
    return [];
  }
  if (nonJokerRanks.length === 1) {
    const [rank] = nonJokerRanks;
    return jokerAllowedRanks.includes(rank) && validRanks.has(rank)
      ? [rank]
      : [];
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
    headline =
      currentGameState() === "PLAYERS_CHOOSE_PUBLIC_CARDS"
        ? "Choose your cards"
        : "It's your turn!";
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
  const exists = state.selectedCards.some(
    (selected) => cardId(selected) === cardId(card),
  );
  if (exists) {
    state.selectedCards = state.selectedCards.filter(
      (selected) => cardId(selected) !== cardId(card),
    );
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
    } else if (
      selectedHasJoker() &&
      nonJokerRank === null &&
      state.selectedCards.length > 0
    ) {
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
  clearMotionState();
  state.inviteCode = payload.invite_code;
  state.playerToken = payload.player_token;
  state.seat = payload.seat;
  state.snapshot = { type: "session_snapshot", data: payload.snapshot };
  state.privateState = { type: "private_state", data: payload.private_state };
  state.presenceNow = Date.now();
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
  return (
    ["auth", "not_found"].includes(error.kind) ||
    [400, 401, 403, 404].includes(error.status)
  );
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
      clearSession(
        "Your saved session is no longer available. Join the game again if it is still active.",
      );
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
      const previousSnapshot = state.snapshot?.data || null;
      state.snapshot = payload;
      state.presenceNow = Date.now();
      detectAnimationEvents(previousSnapshot, payload.data);
      if (!payload.data.players.some((player) => player.seat === state.seat)) {
        clearSession(
          "Your saved session is no longer available. Join the game again if it is still active.",
        );
        return;
      }
      syncKickSeatConfirmation(payload.data);
      syncTurnNotice(payload.data);
      if (payload.data.status === "LOBBY" && previousSnapshot?.status === "GAME_OVER") {
        clearGameStateForLobby();
      }
      if (payload.data.status === "GAME_OVER" || !isMyTurn()) {
        resetSelection();
      }
      render();
    } else if (payload.type === "private_state") {
      const previousPrivateCards =
        state.privateState?.data?.private_cards || [];
      state.privateState = payload;
      if (
        state.pendingLocalPlay &&
        Number.isInteger(state.pendingLocalPlay.expectedDrawCount) &&
        state.pendingLocalPlay.expectedDrawCount > 0
      ) {
        state.pendingLocalDrawAnimation = collectAddedCards(
          previousPrivateCards,
          payload.data.private_cards || [],
          state.pendingLocalPlay.expectedDrawCount,
        );
      }
      state.hiddenLocalHandCardIds = [];
      state.pendingLocalPlay = null;
      if (isShoutoutOnCooldown(payload.data)) {
        state.shoutoutMenuOpen = false;
      }
      if (
        payload.data.pending_joker_selection ||
        payload.data.pending_hidden_take
      ) {
        state.selectedCards = [];
        state.jokerRank =
          payload.data.pending_joker_card?.effective_rank || null;
        state.highLowChoice = "";
      }
      render();
    } else if (payload.type === "shoutout") {
      if (!rememberShoutoutEvent(payload.data?.event_id || "")) {
        return;
      }
      queueAnimation({
        kind: "shoutout",
        eventId: payload.data.event_id || "",
        seat: payload.data.seat,
        preset: payload.data.preset,
        duration: prefersReducedMotion() ? 320 : 1500,
      });
      render();
    } else if (payload.type === "action_error") {
      clearPendingLocalPlay();
      state.pendingLocalDrawAnimation = null;
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
      clearSession(
        "Your saved session is no longer available. Join the game again if it is still active.",
      );
      return;
    }
    render();
    scheduleReconnect();
  });
}

async function startGame() {
  try {
    const previousSnapshot = state.snapshot?.data || null;
    const response = await api(`/api/games/${state.inviteCode}/start`, {
      method: "POST",
      body: JSON.stringify({ player_token: state.playerToken }),
    });
    state.snapshot = response;
    detectAnimationEvents(previousSnapshot, response.data);
    state.error = "";
    syncTurnNotice(response.data);
    render();
  } catch (error) {
    state.error = error.message;
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
    state.snapshot = response;
    state.error = "";
    syncTurnNotice(response.data, { suppress: true });
    render();
  } catch (error) {
    state.error = error.message;
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
    state.snapshot = response;
    state.error = "";
    render();
  } catch (error) {
    state.error = error.message;
    render();
  }
}

async function kickPlayer(seat) {
  try {
    const response = await api(
      `/api/games/${state.inviteCode}/players/${seat}/kick`,
      {
        method: "POST",
        body: JSON.stringify({ player_token: state.playerToken }),
      },
    );
    resetKickSeatConfirmation();
    state.snapshot = response;
    state.error = "";
    syncTurnNotice(response.data);
    render();
  } catch (error) {
    state.error = error.message;
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
  if (state.localPlaySendTimer !== null) {
    return;
  }
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
    state.error =
      "Choose whether the next player must go higher or may go lower.";
    render();
    return;
  }
  const selectedCards = [...state.selectedCards];
  const payload = {
    type: "play_private_cards",
    cards: selectedCards,
    choice:
      playRank() === state.snapshot.data.rules.high_low_rank
        ? state.highLowChoice
        : "",
    joker_rank: selectedHasJoker() ? state.jokerRank : null,
  };
  const capturedCards = captureLocalPlaySelection();
  const shouldStageLocalThrow =
    !prefersReducedMotion() &&
    Array.isArray(capturedCards) &&
    capturedCards.length > 0;
  if (!shouldStageLocalThrow) {
    sendAction(payload);
    resetSelection();
    return;
  }

  const throwCards = buildLocalPlayThrowMotions(capturedCards);
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
  state.hiddenLocalHandCardIds = capturedCards.map((entry) =>
    cardId(entry.card),
  );
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
  }, 140);
}

function submitTakePile() {
  sendAction({ type: "take_play_pile" });
}

function submitShoutout(shoutoutKey) {
  if (!shoutoutKey) {
    return;
  }
  closeShoutoutMenu();
  state.error = "";
  const sent = sendAction({ type: "send_shoutout", shoutout_key: shoutoutKey });
  if (!sent) {
    return;
  }
  primeLocalShoutoutCooldown();
  render();
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
  const pendingCard = pendingJokerCard();
  const pendingRevealedJoker = isJokerCard(pendingCard);
  const needsHighLowChoice = pendingRevealedJoker
    ? state.jokerRank === state.snapshot.data.rules.high_low_rank
    : true;

  if (pendingRevealedJoker) {
    if (!state.jokerRank) {
      state.error = "Choose what the joker should be first.";
      render();
      return;
    }
    if (needsHighLowChoice && !["HIGHER", "LOWER"].includes(state.highLowChoice)) {
      state.error =
        "Choose whether the next player must go higher or may go lower.";
      render();
      return;
    }
  } else if (!["HIGHER", "LOWER"].includes(state.highLowChoice)) {
    state.error =
      "Choose whether the next player must go higher or may go lower.";
    render();
    return;
  }

  const choice = pendingRevealedJoker
    ? needsHighLowChoice
      ? state.highLowChoice
      : ""
    : state.highLowChoice;

  sendAction({
    type: "resolve_joker",
    choice,
    joker_rank: pendingRevealedJoker ? state.jokerRank : null,
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

function relativeSeatIndex(snapshot, player) {
  if (state.seat === null || snapshot.players.length === 0) {
    return player.seat;
  }
  return (
    (player.seat - state.seat + snapshot.players.length) %
    snapshot.players.length
  );
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

function shoutoutOffsetForSeat(snapshot, player) {
  const position = seatPositionClass(snapshot, player);
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

function playerMap(snapshot) {
  return new Map(
    (snapshot?.players || []).map((player) => [player.seat, player]),
  );
}

function hasActiveMotion(kind) {
  return state.animations.some((animation) => animation.kind === kind);
}

function seatHasActiveMotion(seat, kinds) {
  return state.animations.some(
    (animation) => kinds.includes(animation.kind) && animation.seat === seat,
  );
}

function motionAnchorKeyForSeat(seat, purpose = "seat") {
  if (purpose === "hand" && seat === state.seat) {
    return "hand-self";
  }
  return `seat-${purpose}-${seat}`;
}

function getMotionAnchor(key) {
  return key ? state.motionAnchors[key] || null : null;
}

function resolveMotionAnchor(...keys) {
  for (const key of keys.flat()) {
    const anchor = getMotionAnchor(key);
    if (anchor) {
      return anchor;
    }
  }
  return null;
}

function measureMotionAnchors() {
  const root = document.querySelector(".game-screen");
  if (!root) {
    state.motionAnchors = {};
    state.motionAnchorSignature = "";
    return false;
  }

  const rootRect = root.getBoundingClientRect();
  const nextAnchors = {};
  root.querySelectorAll("[data-motion-anchor]").forEach((element) => {
    const key = element.dataset.motionAnchor;
    if (!key) {
      return;
    }
    const rect = element.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) {
      return;
    }
    nextAnchors[key] = {
      x: rect.left - rootRect.left + rect.width / 2,
      y: rect.top - rootRect.top + rect.height / 2,
    };
  });

  const signature = Object.entries(nextAnchors)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(
      ([key, point]) => `${key}:${Math.round(point.x)}:${Math.round(point.y)}`,
    )
    .join("|");
  const changed = signature !== state.motionAnchorSignature;
  state.motionAnchors = nextAnchors;
  state.motionAnchorSignature = signature;
  return changed;
}

function getGameScreenRoot() {
  return document.querySelector(".game-screen");
}

function rectWithinGameScreen(element) {
  const root = getGameScreenRoot();
  if (!root || !element) {
    return null;
  }
  const rootRect = root.getBoundingClientRect();
  const rect = element.getBoundingClientRect();
  if (rect.width === 0 && rect.height === 0) {
    return null;
  }
  return {
    left: rect.left - rootRect.left,
    top: rect.top - rootRect.top,
    width: rect.width,
    height: rect.height,
  };
}

function centerToRect(center, width, height) {
  return {
    left: center.x - width / 2,
    top: center.y - height / 2,
    width,
    height,
  };
}

function getPileTopRect() {
  const explicit = document.querySelector('[data-motion-rect="pile-top"]');
  if (explicit) {
    return rectWithinGameScreen(explicit);
  }
  const anchor = resolveMotionAnchor("pile");
  if (!anchor) {
    return null;
  }
  return centerToRect(anchor, 38, 52);
}

function getDeckTopRect() {
  const explicit = document.querySelector('[data-motion-rect="deck-top"]');
  if (explicit) {
    return rectWithinGameScreen(explicit);
  }
  const anchor = resolveMotionAnchor("deck");
  if (!anchor) {
    return null;
  }
  return centerToRect(anchor, 42, 58);
}

function getHandCenterRect() {
  const handFan = document.querySelector(".hand-fan");
  if (!handFan) {
    return null;
  }
  const handRect = rectWithinGameScreen(handFan);
  if (!handRect) {
    return null;
  }
  const visibleCard = handFan.querySelector(".card");
  const cardRect = visibleCard ? rectWithinGameScreen(visibleCard) : null;
  const styles = window.getComputedStyle(handFan);
  const fallbackWidth =
    Number.parseFloat(styles.getPropertyValue("--hand-card-width")) || 72;
  const fallbackHeight =
    Number.parseFloat(styles.getPropertyValue("--hand-card-height")) || 102;
  const width = cardRect?.width || fallbackWidth;
  const height = cardRect?.height || fallbackHeight;
  return {
    left: handRect.left + (handRect.width - width) / 2,
    top: handRect.top + (handRect.height - height) / 2,
    width,
    height,
  };
}

function offsetRect(rect, deltaX = 0, deltaY = 0) {
  return {
    left: rect.left + deltaX,
    top: rect.top + deltaY,
    width: rect.width,
    height: rect.height,
  };
}

function captureLocalPlaySelection() {
  if (prefersReducedMotion()) {
    return null;
  }
  const root = getGameScreenRoot();
  if (!root || state.selectedCards.length === 0) {
    return null;
  }
  const rootRect = root.getBoundingClientRect();
  const captures = state.selectedCards
    .map((card, index) => {
      const element = root.querySelector(
        `.hand-fan [data-card-id="${cardId(card)}"]`,
      );
      if (!element) {
        return null;
      }
      const rect = element.getBoundingClientRect();
      return {
        card,
        index,
        fromRect: {
          left: rect.left - rootRect.left,
          top: rect.top - rootRect.top,
          width: rect.width,
          height: rect.height,
        },
      };
    })
    .filter(Boolean);
  return captures.length > 0 ? captures : null;
}

function buildLocalPlayThrowMotions(captures) {
  if (!captures || captures.length === 0) {
    return [];
  }
  return captures.slice(0, 3).map((capture, index) => {
    const throwRect = buildLocalPlayThrowRect(
      capture.fromRect,
      index,
      Math.min(captures.length, 3),
    );
    return {
      kind: "local-play-throw",
      card: capture.card,
      fromRect: capture.fromRect,
      toRect: throwRect,
      delay: index * 70,
      rotate: index % 2 === 0 ? -8 : 7,
      duration: 320,
    };
  });
}

function buildLocalPlayThrowRect(fromRect, index, totalCount) {
  const pileRect = getPileTopRect();
  const fallbackHandRect = getHandCenterRect();
  const fromCenterX = fromRect.left + fromRect.width / 2;
  const fromCenterY = fromRect.top + fromRect.height / 2;
  const fallbackTargetX = fallbackHandRect
    ? fallbackHandRect.left + fallbackHandRect.width / 2
    : fromCenterX;
  const fallbackTargetY = fallbackHandRect
    ? fallbackHandRect.top - 130
    : fromCenterY - 150;
  const targetCenterX = pileRect
    ? pileRect.left + pileRect.width / 2
    : fallbackTargetX;
  const targetCenterY = pileRect
    ? pileRect.top + pileRect.height / 2
    : fallbackTargetY;
  const laneOffset = (index - (totalCount - 1) / 2) * 28;
  const waypointCenterX =
    fromCenterX + (targetCenterX - fromCenterX) * 0.64 + laneOffset;
  const waypointCenterY =
    fromCenterY + (targetCenterY - fromCenterY) * 0.46 - 54 - index * 4;
  return {
    left: waypointCenterX - (fromRect.width * 0.92) / 2,
    top: waypointCenterY - (fromRect.height * 0.92) / 2,
    width: fromRect.width * 0.92,
    height: fromRect.height * 0.92,
  };
}

function buildLocalPlaySettleMotions(throwCards) {
  const pileRect = getPileTopRect();
  if (!throwCards || throwCards.length === 0 || !pileRect) {
    return [];
  }
  return throwCards.slice(0, 3).map((capture, index) => {
    const spread = (index - (Math.min(throwCards.length, 3) - 1) / 2) * 10;
    return {
      kind: "local-play-settle",
      card: capture.card,
      fromRect: capture.fromRect,
      toRect: offsetRect(pileRect, spread, index * 2),
      delay: index * 52,
      rotate: capture.rotate ?? (index % 2 === 0 ? -3 : 3),
      duration: 250,
    };
  });
}

function buildLocalDrawMotions(cards) {
  const deckRect = getDeckTopRect();
  const handRect = getHandCenterRect();
  if (!deckRect || !handRect || !cards || cards.length === 0) {
    return [];
  }
  return cards.slice(0, 3).map((card, index) => {
    const spread = (index - (Math.min(cards.length, 3) - 1) / 2) * 16;
    return {
      kind: "local-draw-settle",
      card,
      fromRect: offsetRect(deckRect, index * 4, index * 3),
      toRect: offsetRect(handRect, spread, 0),
      delay: index * 65,
      rotate: index % 2 === 0 ? -6 : 5,
      duration: 520,
    };
  });
}

function flushPendingLocalMotions() {
  let changed = false;

  if (state.pendingLocalPlay?.throwCards) {
    const motions = buildLocalPlaySettleMotions(
      state.pendingLocalPlay.throwCards,
    );
    state.pendingLocalPlay.throwCards = null;
    if (motions.length > 0) {
      motions.forEach((motion) => queueLocalMotion(motion));
      changed = true;
    }
  }

  if (Array.isArray(state.pendingLocalDrawAnimation)) {
    const motions = buildLocalDrawMotions(state.pendingLocalDrawAnimation);
    state.pendingLocalDrawAnimation = null;
    if (motions.length > 0) {
      motions.forEach((motion) => queueLocalMotion(motion));
      changed = true;
    }
  }

  return changed;
}

function detectPlaySource(previousSnapshot, snapshot, previousPlayers) {
  const localPrivateCards = state.privateState?.data?.private_cards || [];
  const localPreviousPlayer = Number.isInteger(state.seat)
    ? previousPlayers.get(state.seat)
    : null;
  const localPlayer = Number.isInteger(state.seat)
    ? snapshot.players.find((entry) => entry.seat === state.seat) || null
    : null;
  const localDeckDraw = snapshot.cards_in_deck < previousSnapshot.cards_in_deck;
  const localPrivateHandWasVisible = localPrivateCards.length > 0;
  const localWasActing = previousSnapshot.current_turn_seat === state.seat;

  if (
    localWasActing &&
    localDeckDraw &&
    localPrivateHandWasVisible &&
    localPlayer &&
    localPreviousPlayer
  ) {
    return { seat: state.seat, source: "hand-self" };
  }

  const candidateSeats = [
    previousSnapshot.current_turn_seat,
    snapshot.current_turn_seat,
    ...snapshot.players.map((player) => player.seat),
  ].filter(
    (seat, index, list) =>
      Number.isInteger(seat) && list.indexOf(seat) === index,
  );

  for (const seat of candidateSeats) {
    const previousPlayer = previousPlayers.get(seat);
    const player = snapshot.players.find((entry) => entry.seat === seat);
    if (!previousPlayer || !player) {
      continue;
    }

    if (player.private_cards_count < previousPlayer.private_cards_count) {
      return { seat, source: seat === state.seat ? "hand-self" : "hand" };
    }

    if (player.public_cards.length < previousPlayer.public_cards.length) {
      return { seat, source: "public" };
    }
  }

  const fallbackSeat = candidateSeats.find((seat) => Number.isInteger(seat));
  if (Number.isInteger(fallbackSeat)) {
    return {
      seat: fallbackSeat,
      source: fallbackSeat === state.seat ? "hand-self" : "hand",
    };
  }

  return null;
}

function detectAnimationEvents(previousSnapshot, snapshot) {
  if (
    !previousSnapshot ||
    previousSnapshot.invite_code !== snapshot.invite_code
  ) {
    return;
  }

  if (
    previousSnapshot.status === "LOBBY" &&
    snapshot.status === "IN_GAME" &&
    snapshot.game_state === "PLAYERS_CHOOSE_PUBLIC_CARDS"
  ) {
    queueAnimation({
      kind: "deal",
      targets: snapshot.players.map((player) => player.seat),
      duration: 760,
    });
  }

  if (
    snapshot.status === "IN_GAME" &&
    Number.isInteger(snapshot.current_turn_seat) &&
    previousSnapshot.current_turn_seat !== snapshot.current_turn_seat
  ) {
    markTurnArrival(snapshot.current_turn_seat);
  }

  const previousPlayers = playerMap(previousSnapshot);
  const lockedSeats = [];
  let revealHiddenSeat = null;

  snapshot.players.forEach((player) => {
    const previousPlayer = previousPlayers.get(player.seat);
    if (!previousPlayer) {
      return;
    }

    if (
      previousSnapshot.game_state === "PLAYERS_CHOOSE_PUBLIC_CARDS" &&
      player.public_cards.length > previousPlayer.public_cards.length
    ) {
      lockedSeats.push({
        seat: player.seat,
        count: player.public_cards.length - previousPlayer.public_cards.length,
      });
    }

    if (
      player.hidden_cards_count < previousPlayer.hidden_cards_count &&
      snapshot.play_pile.length > previousSnapshot.play_pile.length &&
      player.private_cards_count === previousPlayer.private_cards_count &&
      player.public_cards.length === previousPlayer.public_cards.length
    ) {
      revealHiddenSeat = player.seat;
    }
  });

  lockedSeats.forEach(({ seat, count }) =>
    queueAnimation({
      kind: "lock",
      seat,
      count: Math.max(1, Math.min(count, 3)),
      duration: 460,
    }),
  );

  if (
    snapshot.status !== "IN_GAME" ||
    previousSnapshot.status !== "IN_GAME" ||
    !previousSnapshot.game_state ||
    !snapshot.game_state
  ) {
    return;
  }

  if (revealHiddenSeat !== null) {
    queueAnimation({
      kind: "reveal-hidden",
      seat: revealHiddenSeat,
      count: 1,
      duration: 430,
    });
  }

  if (
    previousSnapshot.play_pile.length > 0 &&
    snapshot.play_pile.length === 0
  ) {
    if ((snapshot.status_message || "").includes("Burn!")) {
      queueAnimation({ kind: "burn", duration: 620 });
      return;
    }

    const takeSeat = snapshot.players.find((player) => {
      const previousPlayer = previousPlayers.get(player.seat);
      return (
        previousPlayer &&
        player.private_cards_count > previousPlayer.private_cards_count
      );
    })?.seat;

    if (Number.isInteger(takeSeat)) {
      queueAnimation({
        kind: "take-pile",
        seat: takeSeat,
        count: Math.min(previousSnapshot.play_pile.length, 4),
        duration: 520,
      });
    }
    return;
  }

  if (
    snapshot.play_pile.length > previousSnapshot.play_pile.length &&
    revealHiddenSeat === null
  ) {
    const playSource = detectPlaySource(
      previousSnapshot,
      snapshot,
      previousPlayers,
    );
    if (playSource && Number.isInteger(playSource.seat)) {
      const deckCardsDrawn = Math.max(
        0,
        previousSnapshot.cards_in_deck - snapshot.cards_in_deck,
      );
      const canUseLocalMorph =
        !prefersReducedMotion() &&
        playSource.seat === state.seat &&
        playSource.source === "hand-self" &&
        state.pendingLocalPlay &&
        Array.isArray(state.pendingLocalPlay.throwCards) &&
        state.pendingLocalPlay.throwCards.length > 0;
      if (canUseLocalMorph) {
        state.pendingLocalPlay.throwCards =
          state.pendingLocalPlay.throwCards.slice(
            0,
            Math.min(
              snapshot.play_pile.length - previousSnapshot.play_pile.length,
              3,
            ),
          );
        if (deckCardsDrawn > 0) {
          state.pendingLocalPlay.expectedDrawCount = Math.min(
            deckCardsDrawn,
            3,
          );
        }
        return;
      }
      clearPendingLocalPlay();
      queueAnimation({
        kind: "play",
        seat: playSource.seat,
        source: playSource.source,
        count: Math.min(
          snapshot.play_pile.length - previousSnapshot.play_pile.length,
          3,
        ),
        duration: 440,
      });
      if (
        playSource.seat === state.seat &&
        playSource.source === "hand-self" &&
        deckCardsDrawn > 0
      ) {
        queueAnimation({
          kind: "draw-self",
          seat: state.seat,
          count: Math.min(deckCardsDrawn, 3),
          duration: 420,
        });
      }
    }
  }
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
      <span class="seat-mini-suit">${isJoker ? (card.effective_rank ? rankLabel(card.effective_rank) : "?") : suitLabel(card.suit)}</span>
    </span>
  `;
}

function renderSeatPublicStack(publicCards, hiddenCardsCount) {
  if (publicCards.length === 0) {
    return hiddenCardsCount > 0
      ? renderSeatHiddenStack(hiddenCardsCount)
      : '<span class="seat-muted">No table cards</span>';
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
  const placementBadge = placementBadgeForPlayer(snapshot, player);
  const seatClasses = [
    "seat-panel",
    seatPositionClass(snapshot, player),
    isCurrentTurn ? "current-turn" : "",
    state.turnArrivalSeat === player.seat ? "turn-arrival" : "",
    isWinner ? "winner" : "",
    isYou ? "you" : "",
    seatHasActiveMotion(player.seat, ["deal"]) ? "motion-deal-target" : "",
    seatHasActiveMotion(player.seat, ["lock"]) ? "motion-lock-target" : "",
    seatHasActiveMotion(player.seat, ["take-pile"]) ? "motion-take-target" : "",
    seatHasActiveMotion(player.seat, ["reveal-hidden"])
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
    !player.is_connected ? '<span class="seat-badge seat-badge-meta">Offline</span>' : "",
  ]
    .filter(Boolean)
    .join("");

  return `
    <div class="${seatClasses}" data-motion-anchor="seat-seat-${player.seat}">
      ${seatBadges ? `<div class="seat-badge-rail">${seatBadges}</div>` : ""}
      <div class="seat-header">
        <div class="seat-title-row">
          <strong>${escapeHtml(player.display_name)}</strong>
        </div>
      </div>
      ${renderOfflinePresence(player)}
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

function isMobileActiveGameLayout(snapshot = state.snapshot?.data) {
  return Boolean(snapshot);
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

function currentPrompt(snapshot) {
  const turnTarget =
    snapshot.current_turn_display_name ||
    (Number.isInteger(snapshot.current_turn_seat)
      ? `Seat ${snapshot.current_turn_seat}`
      : "the next player");
  if (snapshot.status === "LOBBY") {
    return "Share the code, wait for enough players, then start.";
  }
  if (snapshot.status === "GAME_OVER") {
    return "Game over. The host can start a rematch.";
  }
  if (canChoosePublicCards()) {
    return "Pick 3 public cards for the table.";
  }
  if (currentGameState() === "DURING_GAME" && isMyTurn()) {
    if (hasPendingJokerSelection()) {
      if (isJokerCard(pendingJokerCard())) {
        return "Choose which rank the revealed joker should be.";
      }
      return "Choose how the revealed 7 changes the next player's turn.";
    }
    if (selectedHasJoker() && !state.jokerRank) {
      return "Choose which rank the joker should be before playing.";
    }
    if (playRank() === snapshot.rules.high_low_rank) {
      return "Choose how the 7 changes the next player's turn.";
    }
    if (hasPendingHiddenTake()) {
      return "Your revealed hidden card cannot be played. Take the pile.";
    }
    if (canPlayHiddenCard()) {
      if (canOptionallyTakePile(snapshot)) {
        return "Reveal a hidden card or take the pile.";
      }
      return "Your hidden cards are live. Reveal a hidden card.";
    }
    if (mustTakePile(snapshot)) {
      return "No legal card to play. Take the pile.";
    }
    if (canOptionallyTakePile(snapshot)) {
      return "Tap matching cards from your hand or take the pile.";
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
                <p>Switching tabs or apps is okay for a while. Live games can still reset after a deploy, restart, or a long period of inactivity.</p>
              </section>
            </div>
            <div class="landing-form-row">
              ${landingBuckets.join("")}
            </div>
            ${
              showSavedSessionCard
                ? `
              <div class="landing-table-banner-row landing-table-banner-row-bottom">
                <section class="landing-table-banner landing-table-resume stack">
                  <div>
                    <strong>${state.restoringSession ? "Restoring your game" : "Resume saved game"}</strong>
                    <p class="muted">
                      ${
                        state.restoringSession
                          ? "Reclaiming your seat and reconnecting to live updates."
                          : "A saved game was found on this device. You can restore it or forget it."
                      }
                    </p>
                  </div>
                  <div class="status-strip">
                    <span class="status-chip">Invite ${escapeHtml(state.inviteCode)}</span>
                    ${state.displayName ? `<span class="status-chip">${escapeHtml(state.displayName)}</span>` : ""}
                  </div>
                  ${state.error ? `<div class="dock-error">${escapeHtml(state.error)}</div>` : ""}
                  ${
                    !state.restoringSession
                      ? `
                    <div class="secondary-action-row">
                      <button class="button accent" id="restore-session">Restore saved session</button>
                      <button class="button secondary" id="forget-session">Forget saved session</button>
                    </div>
                  `
                      : ""
                  }
                </section>
              </div>
            `
                : state.error
                  ? `
              <div class="landing-table-banner-row landing-table-banner-row-bottom">
                <section class="landing-table-banner landing-table-error">
                  <strong>${escapeHtml(state.error)}</strong>
                </section>
              </div>
            `
                  : ""
            }
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
  const isHost = me()?.is_host;

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
      ${
        isHost
          ? `
        <div class="primary-action-row">
          <button class="button accent full-width" id="rematch-game" type="button">Rematch</button>
        </div>
      `
          : `
        <p class="muted tiny">Waiting for the host to start a rematch.</p>
      `
      }
    </section>
  `;
}

function renderActions(snapshot) {
  const cards = privateCards();
  const selectedIds = new Set(state.selectedCards.map((card) => cardId(card)));
  const pendingCard = pendingJokerCard();
  const pendingJoker = hasPendingJokerSelection();
  const pendingRevealedJoker = pendingJoker && isJokerCard(pendingCard);
  const currentPendingRank = pendingJoker
    ? cardEffectiveRank(pendingCard)
    : null;
  const choosingPublicCards = canChoosePublicCards();
  const isPlayDecisionPhase =
    currentGameState() === "DURING_GAME" && isMyTurn();
  const allowJokerDefinition =
    isPlayDecisionPhase && (pendingRevealedJoker || selectedHasJoker());
  const jokerChoices = pendingJoker
    ? jokerOptions(snapshot, [pendingCard])
    : jokerOptions(snapshot);
  const currentPlayRank = pendingJoker
    ? pendingRevealedJoker
      ? state.jokerRank
      : currentPendingRank
    : playRank();
  const showHighLowChoice =
    isPlayDecisionPhase &&
    !choosingPublicCards &&
    currentPlayRank === snapshot.rules.high_low_rank;
  const hasHighLowChoice = ["HIGHER", "LOWER"].includes(state.highLowChoice);
  const turnName =
    snapshot.current_turn_display_name ||
    (Number.isInteger(snapshot.current_turn_seat)
      ? `Seat ${snapshot.current_turn_seat}`
      : "the next player");
  const layout = handLayout(snapshot);
  const showTakePileOverlay = mustTakePile(snapshot);
  const showHiddenAction = canPlayHiddenCard();
  const showMobileTurnPrompt =
    isMobileActiveGameLayout(snapshot) && currentGameState() === "DURING_GAME";
  const showPlaySelectedAction =
    currentGameState() === "DURING_GAME" &&
    isMyTurn() &&
    !showHiddenAction &&
    !showTakePileOverlay &&
    !pendingJoker;
  const playSelectedDisabled =
    cards.length === 0 ||
    (selectedHasJoker() && !state.jokerRank) ||
    (showHighLowChoice && !hasHighLowChoice);
  let handPrimaryAction = null;
  if (choosingPublicCards) {
    handPrimaryAction = {
      action: "choose-public",
      label: "Lock cards",
      disabled: false,
    };
  } else if (pendingJoker) {
    handPrimaryAction = {
      action: "resolve-joker",
      label: pendingRevealedJoker ? "Play joker" : "Play revealed card",
      disabled:
        (pendingRevealedJoker && state.jokerRank === null) ||
        (showHighLowChoice && !hasHighLowChoice),
    };
  } else if (showHiddenAction) {
    handPrimaryAction = {
      action: "play-hidden",
      label: "Reveal hidden card",
      disabled: false,
    };
  } else if (showPlaySelectedAction) {
    handPrimaryAction = {
      action: "play-cards",
      label: "Play cards",
      disabled: playSelectedDisabled,
    };
  }
  const dockClasses = [
    "panel",
    "hand-dock",
    layout.classes,
    seatHasActiveMotion(state.seat, ["deal"]) ? "motion-deal-target" : "",
    seatHasActiveMotion(state.seat, ["lock"]) ? "motion-lock-target" : "",
    seatHasActiveMotion(state.seat, ["play"]) ? "motion-play-target" : "",
    hasActiveMotion("draw-self") ? "motion-draw-target" : "",
    seatHasActiveMotion(state.seat, ["take-pile"]) ? "motion-take-target" : "",
    state.turnArrivalSeat === state.seat ? "turn-arrival" : "",
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
        ${
          handPrimaryAction
            ? `
          <button
            class="button accent button-inline dock-header-action"
            id="hand-primary-action"
            data-hand-action="${handPrimaryAction.action}"
            ${handPrimaryAction.disabled ? "disabled" : ""}
          >${handPrimaryAction.label}</button>
        `
            : ""
        }
      </div>
      <div class="dock-prompt">${escapeHtml(currentPrompt(snapshot))}</div>
      ${state.error ? `<div class="dock-error">${escapeHtml(state.error)}</div>` : ""}
      ${
        pendingJoker
          ? `
        <div class="joker-pending-card">
          ${renderCard(pendingCard, false, false)}
        </div>
      `
          : `
        <div class="hand-fan" data-motion-anchor="hand-self">
          ${
            cards
              .map((card) =>
                renderCard(
                  card,
                  selectedIds.has(cardId(card)),
                  true,
                  isLocalHandCardHidden(card),
                ),
              )
              .join("") || '<p class="muted">No cards in hand right now.</p>'
          }
        </div>
      `
      }
      <div class="actions">
        ${
          allowJokerDefinition
            ? `
          <div class="choice-block">
            <strong class="choice-title">${pendingRevealedJoker ? "Choose the revealed joker" : "Choose the joker rank"}</strong>
            <div class="joker-choice-row">
              ${jokerChoices
                .map(
                  (rank) => `
                <button
                  class="button ${state.jokerRank === rank ? "accent" : "secondary"}"
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
          showHighLowChoice
            ? `
          <div class="choice-block">
            <div class="choice-row">
              <button class="button ${state.highLowChoice === "LOWER" ? "accent" : "secondary"}" id="choose-lower">7 or lower</button>
              <button class="button ${state.highLowChoice === "HIGHER" ? "accent" : "secondary"}" id="choose-higher">7 or higher</button>
            </div>
          </div>
        `
            : ""
        }
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
      ${
        showCompactBrand
          ? `
        <div class="game-topbar-title">
          <strong class="game-topbar-name">Shithead</strong>
          <span class="game-topbar-eyebrow">Private Mobile Alpha</span>
        </div>
      `
          : ""
      }
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
  if (!mustTakePile(snapshot) && !canOptionallyTakePile(snapshot)) {
    return "";
  }

  return `
    <button class="button accent pile-action" id="take-pile-overlay">
      Take pile
    </button>
  `;
}

function renderMotionGhost(kind, from, to, index = 0) {
  if (!from || !to) {
    return "";
  }
  return `
    <span
      class="motion-card motion-${kind}"
      style="
        --motion-x:${Math.round(from.x)}px;
        --motion-y:${Math.round(from.y)}px;
        --motion-dx:${Math.round(to.x - from.x)}px;
        --motion-dy:${Math.round(to.y - from.y)}px;
        --motion-delay:${index * 60}ms;
        --motion-rotate:${index % 2 === 0 ? -7 : 6}deg;
      "
      aria-hidden="true"
    ></span>
  `;
}

function renderLocalMotionCard(animation) {
  const source = animation.fromRect;
  const target = animation.toRect;
  if (!source || !target) {
    return "";
  }
  const scaleX = target.width / Math.max(source.width, 1);
  const scaleY = target.height / Math.max(source.height, 1);
  return `
    <span
      class="motion-card motion-local motion-${animation.kind}"
      style="
        --motion-left:${Math.round(source.left)}px;
        --motion-top:${Math.round(source.top)}px;
        --motion-width:${Math.round(source.width)}px;
        --motion-height:${Math.round(source.height)}px;
        --motion-dx:${Math.round(target.left - source.left)}px;
        --motion-dy:${Math.round(target.top - source.top)}px;
        --motion-scale-x:${scaleX.toFixed(3)};
        --motion-scale-y:${scaleY.toFixed(3)};
        --motion-delay:${animation.delay || 0}ms;
        --motion-rotate:${animation.rotate || 0}deg;
      "
      aria-hidden="true"
    >
      <span class="motion-card-shell">
        <span class="card motion-card-face ${isJokerCard(animation.card) ? "joker" : ""} ${isRedSuit(animation.card.suit) ? "red" : ""}">
          ${renderCardBody(animation.card)}
        </span>
      </span>
    </span>
  `;
}

function renderShoutoutBubble(animation, snapshot) {
  const player = snapshot?.players?.find(
    (entry) => entry.seat === animation.seat,
  );
  const anchor = resolveMotionAnchor(
    motionAnchorKeyForSeat(animation.seat, "seat"),
    `seat-seat-${animation.seat}`,
  );
  if (!player || !anchor) {
    return "";
  }

  const offset = shoutoutOffsetForSeat(snapshot, player);
  const preset = animation.preset || {};
  return `
    <span
      class="motion-shoutout motion-shoutout-${escapeHtml(preset.key || "default")}"
      data-shoutout-event-id="${escapeHtml(animation.eventId || "")}"
      data-shoutout-key="${escapeHtml(preset.key || "")}"
      style="
        left:${Math.round(anchor.x)}px;
        top:${Math.round(anchor.y)}px;
        --shoutout-dx:${Math.round(offset.dx)}px;
        --shoutout-dy:${Math.round(offset.dy)}px;
        --shoutout-dx-soft:${Math.round(offset.dx * 0.72)}px;
        --shoutout-dy-soft:${Math.round(offset.dy * 0.72)}px;
        --shoutout-accent:${escapeHtml(preset.color || "#f4b942")};
      "
      aria-hidden="true"
    >
      <span class="motion-shoutout-body">
        <span class="motion-shoutout-emoji">${escapeHtml(preset.emoji || "✨")}</span>
        <span class="motion-shoutout-label">${escapeHtml(preset.label || "Shoutout")}</span>
      </span>
    </span>
  `;
}

function renderMotionLayer(snapshot) {
  if (
    !snapshot ||
    (state.animations.length === 0 && state.localMotionAnimations.length === 0)
  ) {
    return "";
  }

  const genericMarkup = state.animations
    .map((animation) => {
      if (animation.kind === "deal") {
        return (animation.targets || [])
          .map((seat, index) => {
            const from = resolveMotionAnchor("deck");
            const target = resolveMotionAnchor(
              motionAnchorKeyForSeat(seat, "hand"),
              `seat-seat-${seat}`,
            );
            return renderMotionGhost("deal", from, target, index);
          })
          .join("");
      }

      if (animation.kind === "lock") {
        const from = resolveMotionAnchor(
          motionAnchorKeyForSeat(animation.seat, "hand"),
          `seat-seat-${animation.seat}`,
        );
        const to = resolveMotionAnchor(
          motionAnchorKeyForSeat(animation.seat, "public"),
          `seat-seat-${animation.seat}`,
        );
        return Array.from({ length: animation.count || 3 }, (_, index) =>
          renderMotionGhost("lock", from, to, index),
        ).join("");
      }

      if (animation.kind === "play") {
        const sourceKeys =
          animation.source === "public"
            ? [
                motionAnchorKeyForSeat(animation.seat, "public"),
                motionAnchorKeyForSeat(animation.seat, "hand"),
                `seat-seat-${animation.seat}`,
              ]
            : animation.source === "hand-self"
              ? [
                  "hand-self",
                  motionAnchorKeyForSeat(animation.seat, "hand"),
                  `seat-seat-${animation.seat}`,
                ]
              : [
                  motionAnchorKeyForSeat(animation.seat, "hand"),
                  motionAnchorKeyForSeat(animation.seat, "public"),
                  `seat-seat-${animation.seat}`,
                ];
        const from = resolveMotionAnchor(sourceKeys);
        return Array.from({ length: animation.count || 1 }, (_, index) =>
          renderMotionGhost("play", from, resolveMotionAnchor("pile"), index),
        ).join("");
      }

      if (animation.kind === "shoutout") {
        return renderShoutoutBubble(animation, snapshot);
      }

      if (animation.kind === "draw-self") {
        return Array.from({ length: animation.count || 1 }, (_, index) =>
          renderMotionGhost(
            "draw-self",
            resolveMotionAnchor("deck"),
            resolveMotionAnchor("hand-self"),
            index,
          ),
        ).join("");
      }

      if (animation.kind === "take-pile") {
        const from = resolveMotionAnchor("pile");
        const to = resolveMotionAnchor(
          motionAnchorKeyForSeat(animation.seat, "hand"),
          motionAnchorKeyForSeat(animation.seat, "public"),
          `seat-seat-${animation.seat}`,
        );
        return Array.from({ length: animation.count || 3 }, (_, index) =>
          renderMotionGhost("take-pile", from, to, index),
        ).join("");
      }

      if (animation.kind === "reveal-hidden") {
        return renderMotionGhost(
          "reveal-hidden",
          resolveMotionAnchor(
            motionAnchorKeyForSeat(animation.seat, "hidden"),
            motionAnchorKeyForSeat(animation.seat, "public"),
            `seat-seat-${animation.seat}`,
          ),
          resolveMotionAnchor("pile"),
        );
      }

      if (animation.kind === "burn") {
        const from = resolveMotionAnchor("pile");
        if (!from) {
          return "";
        }
        const offsets = [
          { x: -36, y: -34 },
          { x: -10, y: -54 },
          { x: 18, y: -42 },
          { x: 42, y: -58 },
        ];
        return Array.from({ length: 4 }, (_, index) =>
          renderMotionGhost(
            "burn",
            from,
            {
              x: from.x + offsets[index].x,
              y: from.y + offsets[index].y,
            },
            index,
          ),
        ).join("");
      }

      return "";
    })
    .join("");

  const localMarkup = state.localMotionAnimations
    .map((animation) => renderLocalMotionCard(animation))
    .join("");

  return `<div class="motion-layer" aria-hidden="true">${genericMarkup}${localMarkup}</div>`;
}

function renderRulesMenu() {
  if (!state.rulesMenuOpen) {
    return "";
  }

  const optionalTakeRuleCopy = state.snapshot?.data?.rules
    ?.allow_optional_take_pile
    ? " This table also allows taking the pile voluntarily at the start of your turn."
    : " Some lobbies may enable taking the pile voluntarily at the start of your turn.";

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

function renderShoutoutMenu(snapshot) {
  if (!state.shoutoutMenuOpen || !canSendShoutouts(snapshot) || isShoutoutOnCooldown()) {
    return "";
  }

  const presets = shoutoutPresets(snapshot);
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
        <div class="shoutout-grid">
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

function renderTable(snapshot) {
  const self = me();
  const isHost = self && self.is_host;
  const showLobbyControls = snapshot.status === "LOBBY";
  const showShoutoutControls =
    snapshot.status === "LOBBY" ||
    snapshot.status === "IN_GAME" ||
    snapshot.status === "GAME_OVER";
  const shoutoutReady = showShoutoutControls && canSendShoutouts(snapshot);
  const shoutoutCooldown = shoutoutCooldownState();
  const shoutoutLocked = shoutoutCooldown !== null;
  const shoutoutEnabled = shoutoutReady && !shoutoutLocked;
  const shoutoutFillStyle = [
    `--shoutout-fill-duration:${shoutoutCooldownMs}ms`,
    `--shoutout-fill-delay:${
      shoutoutLocked
        ? `-${Math.min(shoutoutCooldown.elapsedMs, shoutoutCooldown.durationMs)}ms`
        : "0ms"
    }`,
  ].join(";");
  const showMobileLobbyLayout = isMobileLobbyLayout(snapshot);
  const sortedPlayers = [...snapshot.players].sort(
    (left, right) =>
      relativeSeatIndex(snapshot, left) - relativeSeatIndex(snapshot, right),
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
    hasActiveMotion("play") || hasActiveMotion("reveal-hidden")
      ? "settling"
      : "",
    hasActiveMotion("take-pile") ? "taking" : "",
    hasActiveMotion("burn") ? "burning" : "",
  ]
    .filter(Boolean)
    .join(" ");
  const deckStackClasses = [
    "deck-stack",
    hasActiveMotion("deal") ? "dealing" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return `
    <section class="panel table-stage stack">
      ${showMobileLobbyLayout && state.error ? `<div class="dock-error">${escapeHtml(state.error)}</div>` : ""}
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
        ${sortedPlayers.map((player) => renderSeat(snapshot, player)).join("")}
        ${renderTurnToast(snapshot)}
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
              ${renderPileAction(snapshot)}
            </div>
          </div>
        </div>
        ${
          showShoutoutControls
            ? `
          <button
            class="table-shoutout-trigger ${shoutoutEnabled ? "" : "disabled"} ${shoutoutLocked ? "locked" : ""}"
            id="open-shoutout-menu"
            type="button"
            aria-label="Open shoutouts"
            title="${
              !shoutoutReady
                ? "Connecting to the table"
                : shoutoutLocked
                  ? `Shoutouts available in ${Math.max(
                      1,
                      Math.ceil(shoutoutCooldown.remainingMs / 1000),
                    )}s`
                  : "Shoutouts"
            }"
            style="${shoutoutFillStyle};"
            ${shoutoutEnabled ? "" : "disabled"}
          >
            <span class="shoutout-trigger-fill" aria-hidden="true"></span>
            <span class="shoutout-joker-emoji" aria-hidden="true">★</span>
          </button>
        `
            : ""
        }
        <button class="table-help-trigger" id="open-rules-menu" type="button" aria-label="Open rules" title="Rules">?</button>
        ${showShoutoutControls ? renderShoutoutMenu(snapshot) : ""}
        ${renderRulesMenu()}
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

function renderApp() {
  if (!state.snapshot) {
    return renderLanding();
  }

  const snapshot = state.snapshot.data;
  const self = me();
  const localPlayerFinished =
    isMobileActiveGameLayout(snapshot) &&
    Boolean(self?.finished_position != null);
  const showMobileLobbyLayout = isMobileLobbyLayout(snapshot);
  const gameScreenClasses = [
    "game-screen",
    `players-${snapshot.players.length}`,
    isMobileActiveGameLayout(snapshot) ? "mobile-one-screen" : "",
    isMobileActiveGameLayout(snapshot)
      ? `layout-${tableLayoutVariant(snapshot)}`
      : "",
    localPlayerFinished ? "local-player-finished" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return `
    ${renderGameTopbar(snapshot)}
    <section class="${gameScreenClasses}">
      ${renderTable(snapshot)}
      ${showMobileLobbyLayout || localPlayerFinished ? "" : renderActions(snapshot)}
      ${renderMotionLayer(snapshot)}
    </section>
    ${!isMobileActiveGameLayout(snapshot) && state.error ? `<section class="panel error">${escapeHtml(state.error)}</section>` : ""}
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
  const gameScreen = document.querySelector(
    ".game-screen.mobile-one-screen, .landing-screen",
  );
  const handDock = document.querySelector(".hand-dock");

  if (!pageShell || !appRoot || !gameScreen) {
    return;
  }

  const shellRect = pageShell.getBoundingClientRect();
  const appStyles = window.getComputedStyle(appRoot);
  const appGap =
    Number.parseFloat(appStyles.rowGap || appStyles.gap || "0") || 0;
  const screenStyles = window.getComputedStyle(gameScreen);
  const screenGap =
    Number.parseFloat(screenStyles.rowGap || screenStyles.gap || "0") || 0;
  const topbarHeight = topbar?.getBoundingClientRect().height || 0;
  const handHeight = handDock?.getBoundingClientRect().height || 0;
  const availableHeight = Math.max(0, shellRect.height - topbarHeight - appGap);
  const tableHeight = handDock
    ? Math.max(0, availableHeight - handHeight - screenGap)
    : availableHeight;

  root.style.setProperty(
    "--mobile-available-height",
    `${Math.round(availableHeight)}px`,
  );
  root.style.setProperty(
    "--mobile-topbar-height",
    `${Math.round(topbarHeight)}px`,
  );
  root.style.setProperty("--mobile-hand-height", `${Math.round(handHeight)}px`);
  root.style.setProperty(
    "--mobile-table-height",
    `${Math.round(tableHeight)}px`,
  );
}

function wireHandFanInteractions(handFan) {
  handFan.addEventListener(
    "scroll",
    () => {
      state.handFanScrollLeft = handFan.scrollLeft;
    },
    { passive: true },
  );

  handFan.addEventListener(
    "touchstart",
    (event) => {
      if (state.handTouchActiveId !== null) {
        return;
      }
      const touch = event.touches[0];
      if (!touch) {
        return;
      }
      beginHandFanTouch(touch.identifier, touch.clientX, touch.clientY, handFan);
    },
    { passive: true },
  );

  handFan.addEventListener(
    "touchmove",
    (event) => {
      const touch =
        [...event.touches].find(
          (entry) => entry.identifier === state.handTouchActiveId,
        ) || event.touches[0];
      if (!touch || state.handTouchActiveId === null) {
        return;
      }
      updateHandFanTouch(touch.identifier, touch.clientX, touch.clientY, handFan);
    },
    { passive: true },
  );

  const finishTouchDrag = (event) => {
    if (state.handTouchActiveId === null) {
      return;
    }
    const touch = [...event.changedTouches].find(
      (entry) => entry.identifier === state.handTouchActiveId,
    );
    if (!touch) {
      if (event.type === "touchcancel" || event.touches.length === 0) {
        resetHandFanTouchState();
      }
      return;
    }
    finishHandFanTouch(touch.identifier, handFan);
  };

  handFan.addEventListener("touchend", finishTouchDrag, { passive: true });
  handFan.addEventListener("touchcancel", finishTouchDrag, { passive: true });

  if (window.PointerEvent) {
    handFan.addEventListener(
      "pointerdown",
      (event) => {
        if (
          event.pointerType === "touch" ||
          event.button !== 0 ||
          state.handDragActiveInputId !== null
        ) {
          return;
        }
        beginHandFanDrag(event.pointerId, event.clientX, event.clientY, handFan);
      },
      { passive: true },
    );

    handFan.addEventListener(
      "pointermove",
      (event) => {
        if (
          event.pointerType === "touch" ||
          state.handDragActiveInputId !== event.pointerId
        ) {
          return;
        }
        updateHandFanDrag(event.pointerId, event.clientX, event.clientY, handFan);
      },
      { passive: true },
    );

    const finishPointerDrag = (event) => {
      if (
        event.pointerType === "touch" ||
        state.handDragActiveInputId !== event.pointerId
      ) {
        return;
      }
      finishHandFanDrag(event.pointerId, handFan);
      try {
        handFan.releasePointerCapture(event.pointerId);
      } catch (error) {}
    };

    handFan.addEventListener("pointerup", finishPointerDrag, { passive: true });
    handFan.addEventListener("pointercancel", finishPointerDrag, {
      passive: true,
    });
    handFan.addEventListener("lostpointercapture", finishPointerDrag, {
      passive: true,
    });

    handFan.addEventListener("mousedown", (event) => {
      if (event.button !== 0 || state.handDragActiveInputId !== null) {
        return;
      }
      beginHandFanDrag(mouseDragInputId, event.clientX, event.clientY, handFan);
    });

    handFan.addEventListener("mousemove", (event) => {
      if (state.handDragActiveInputId !== mouseDragInputId) {
        return;
      }
      updateHandFanDrag(mouseDragInputId, event.clientX, event.clientY, handFan);
    });

    const finishMouseDrag = () => {
      if (state.handDragActiveInputId !== mouseDragInputId) {
        return;
      }
      finishHandFanDrag(mouseDragInputId, handFan);
    };

    handFan.addEventListener("mouseup", finishMouseDrag);
    handFan.addEventListener("mouseleave", finishMouseDrag);
    return;
  }

  handFan.addEventListener("mousedown", (event) => {
    if (event.button !== 0 || state.handDragActiveInputId !== null) {
      return;
    }
    beginHandFanDrag(mouseDragInputId, event.clientX, event.clientY, handFan);
  });

  handFan.addEventListener("mousemove", (event) => {
    if (state.handDragActiveInputId !== mouseDragInputId) {
      return;
    }
    updateHandFanDrag(mouseDragInputId, event.clientX, event.clientY, handFan);
  });

  const finishMouseDrag = () => {
    if (state.handDragActiveInputId !== mouseDragInputId) {
      return;
    }
    finishHandFanDrag(mouseDragInputId, handFan);
  };

  handFan.addEventListener("mouseup", finishMouseDrag);
  handFan.addEventListener("mouseleave", finishMouseDrag);
}

function wireEvents() {
  app
    .querySelectorAll("form")
    .forEach((form) => form.addEventListener("submit", onSubmit));

  const handFan = app.querySelector(".hand-fan");
  if (handFan) {
    wireHandFanInteractions(handFan);
  }

  app.querySelectorAll("[data-card-id]").forEach((button) => {
    button.addEventListener("click", () => {
      if (Date.now() < state.suppressCardTapUntil) {
        return;
      }
      const card = privateCards().find(
        (entry) => cardId(entry) === button.dataset.cardId,
      );
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

  const rematchButton = document.getElementById("rematch-game");
  if (rematchButton) {
    rematchButton.addEventListener("click", rematchGame);
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
          state.error =
            "Share failed. You can still share the invite link manually.";
        }
      }
      render();
    });
  }

  const optionalTakeToggle = document.getElementById(
    "toggle-optional-take-pile",
  );
  if (optionalTakeToggle) {
    optionalTakeToggle.addEventListener("click", () => {
      updateGameSettings(
        optionalTakeToggle.getAttribute("aria-checked") !== "true",
      );
    });
  }

  app.querySelectorAll("[data-kick-seat]").forEach((button) => {
    button.addEventListener("click", () => {
      handleKickSeatClick(Number(button.dataset.kickSeat));
    });
  });

  const openRulesMenuButton = document.getElementById("open-rules-menu");
  if (openRulesMenuButton) {
    openRulesMenuButton.addEventListener("click", openRulesMenu);
  }

  const openShoutoutMenuButton = document.getElementById("open-shoutout-menu");
  if (openShoutoutMenuButton) {
    openShoutoutMenuButton.addEventListener("click", toggleShoutoutMenu);
  }

  const closeRulesMenuButton = document.getElementById("close-rules-menu");
  if (closeRulesMenuButton) {
    closeRulesMenuButton.addEventListener("click", closeRulesMenu);
  }

  const closeRulesMenuBackdrop = document.getElementById(
    "close-rules-menu-backdrop",
  );
  if (closeRulesMenuBackdrop) {
    closeRulesMenuBackdrop.addEventListener("click", closeRulesMenu);
  }

  const closeShoutoutMenuButton = document.getElementById(
    "close-shoutout-menu",
  );
  if (closeShoutoutMenuButton) {
    closeShoutoutMenuButton.addEventListener("click", closeShoutoutMenu);
  }

  const closeShoutoutMenuBackdrop = document.getElementById(
    "close-shoutout-menu-backdrop",
  );
  if (closeShoutoutMenuBackdrop) {
    closeShoutoutMenuBackdrop.addEventListener("click", closeShoutoutMenu);
  }

  app.querySelectorAll("[data-shoutout-key]").forEach((button) => {
    button.addEventListener("click", () => {
      submitShoutout(button.dataset.shoutoutKey || "");
    });
  });

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

function render({ force = false } = {}) {
  if (!force && isHandInteractionActive()) {
    state.handDragQueuedRender = true;
    return;
  }
  state.handDragQueuedRender = false;
  document.body.classList.toggle(
    "game-active-mobile",
    !state.snapshot || isMobileActiveGameLayout(),
  );
  document.body.classList.toggle(
    "game-started-mobile",
    Boolean(state.snapshot) && state.snapshot.data.status !== "LOBBY",
  );
  syncPresenceTicker();
  syncShoutoutUnlockTimer();
  app.innerHTML = renderApp();
  if (!state.snapshot && state.pendingLandingNameFocus) {
    const joinNameInput = document.getElementById("join-name");
    if (joinNameInput) {
      joinNameInput.focus();
      state.pendingLandingNameFocus = false;
    }
  }
  wireEvents();
  window.requestAnimationFrame(() => {
    syncMobileGameLayout();
    restoreHandFanScroll();
    window.requestAnimationFrame(() => {
      restoreHandFanScroll();
    });
    const anchorsChanged = measureMotionAnchors();
    const queuedLocalMotion = flushPendingLocalMotions();
    if (queuedLocalMotion) {
      if (!state.motionRerenderScheduled) {
        state.motionRerenderScheduled = true;
        window.requestAnimationFrame(() => {
          state.motionRerenderScheduled = false;
          render();
        });
      }
      return;
    }
    if (
      anchorsChanged &&
      state.snapshot &&
      state.animations.length > 0 &&
      !state.motionRerenderScheduled
    ) {
      state.motionRerenderScheduled = true;
      window.requestAnimationFrame(() => {
        state.motionRerenderScheduled = false;
        render();
      });
    }
  });
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
  if (event.key === "Escape" && state.shoutoutMenuOpen) {
    closeShoutoutMenu();
  } else if (event.key === "Escape" && state.rulesMenuOpen) {
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
  navigator.serviceWorker
    .register("/static/sw.js?v=20260404c")
    .then(() => {
      if (navigator.serviceWorker.controller) {
        navigator.serviceWorker.addEventListener("controllerchange", () => {
          window.location.reload();
        });
      }
    })
    .catch(() => {});
}
