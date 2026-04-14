import {
  clearAnimationTimers,
  clearKickSeatConfirmTimer,
  clearLeaveConfirmTimer,
  clearLocalPlaySendTimer,
  clearPendingLocalPlay,
  clearPresenceTicker,
  clearRestoreRetryTimer,
  clearShoutoutUnlockTimer,
  clearTurnArrivalTimer,
  hasSavedSession,
  isHandDragActive,
  isHandInteractionActive,
  loadStoredSession,
  persistSession,
  resetHandFanTouchState,
  resetSelection,
  state,
} from "./frontend/state.js";
import { createSessionController } from "./frontend/session_controller.js";
import { createGameUiController } from "./frontend/game_ui_controller.js";
import {
  renderAppView,
  renderGameTopbarView,
  renderLandingView,
} from "./frontend/view/root.js";
import {
  deriveHandLayout,
  deriveTableLayoutVariant,
  renderGameplayScreenView,
  renderRulesMenuView,
  renderShoutoutMenuView,
} from "./frontend/view/gameplay_screen.js";
import {
  deriveGameplayUiState,
  isJokerCard,
  JOKER_SYMBOL as jokerSymbol,
} from "./frontend/gameplay_ui_state.js";
const shoutoutCooldownMs = 4000;
const cardTapSuppressMs = 350;
const handDragThreshold = 14;
const mouseDragInputId = -1;

const app = document.getElementById("app");
let appDelegatedEventsWired = false;
let sessionController = null;
let gameUiController = null;

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
    sessionController.kickPlayer(seat);
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

function syncShoutoutMenu(menuViewState = buildShoutoutMenuViewState()) {
  const tableMap = document.querySelector(".table-map");
  if (!tableMap) {
    return;
  }

  const currentLayer = document.querySelector(".shoutout-menu-layer");
  if (!menuViewState) {
    if (currentLayer) {
      currentLayer.remove();
    }
    return;
  }
  const menuHtml = renderShoutoutMenuView(menuViewState);
  if (!menuHtml) {
    if (currentLayer) {
      currentLayer.remove();
    }
    return;
  }

  const wrapper = document.createElement("div");
  wrapper.innerHTML = menuHtml;
  const nextLayer = wrapper.firstElementChild;
  if (!nextLayer) {
    if (currentLayer) {
      currentLayer.remove();
    }
    return;
  }

  if (currentLayer) {
    currentLayer.replaceWith(nextLayer);
  } else {
    tableMap.appendChild(nextLayer);
  }
}

function openShoutoutMenu() {
  if (isShoutoutOnCooldown()) {
    state.shoutoutMenuOpen = false;
    syncShoutoutMenu();
    return;
  }
  state.rulesMenuOpen = false;
  state.shoutoutMenuOpen = true;
  document.querySelectorAll(".rules-menu-layer").forEach((element) => {
    element.remove();
  });
  syncShoutoutMenu();
}

function closeShoutoutMenu({ rerender = false } = {}) {
  state.shoutoutMenuOpen = false;
  const currentLayer = document.querySelector(".shoutout-menu-layer");
  if (currentLayer) {
    currentLayer.remove();
  }
  if (rerender) {
    render();
    return;
  }
}

function toggleShoutoutMenu() {
  if (state.shoutoutMenuOpen) {
    closeShoutoutMenu({ rerender: false });
    return;
  }
  openShoutoutMenu();
}

function getMotionOverlayRoot() {
  return document.getElementById("motion-overlay");
}

function getMotionLayerHost() {
  return document.getElementById("motion-layer-host");
}

function ensureMotionLayer() {
  const existingLayer = getMotionLayerHost();
  if (existingLayer) {
    return existingLayer;
  }

  const overlay = getMotionOverlayRoot();
  if (!overlay) {
    return null;
  }

  const layer = document.createElement("div");
  layer.className = "motion-layer";
  layer.id = "motion-layer-host";
  overlay.appendChild(layer);
  return layer;
}

function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
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

function clearSession(errorMessage = "") {
  sessionController?.closeWebSocket();
  gameUiController?.clearTurnNoticeState();
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
  resetSelection();
  state.restoreRetryCount = 0;
  persistSession();
  render({ force: true });
}

function forgetSavedSession() {
  sessionController?.closeWebSocket();
  gameUiController?.clearTurnNoticeState();
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
  resetSelection();
  state.restoreRetryCount = 0;
  persistSession();
  render({ force: true });
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

function shoutoutPresets(snapshot = state.snapshot?.data) {
  return snapshot?.shoutout_presets || [];
}

function shoutoutCooldownState(privateState = state.privateState?.data) {
  const trigger = gameUiController?.shoutoutTriggerState(
    state.snapshot?.data,
    privateState,
  );
  return trigger?.shoutoutCooldown || null;
}

function shoutoutTriggerState(
  snapshot = state.snapshot?.data,
  privateState = state.privateState?.data,
) {
  return (
    gameUiController?.shoutoutTriggerState(snapshot, privateState) || {
      shoutoutReady: false,
      shoutoutCooldown: null,
      shoutoutLocked: false,
      shoutoutEnabled: false,
      shoutoutFillStyle: "",
    }
  );
}

function isShoutoutOnCooldown(privateState = state.privateState?.data) {
  return Boolean(gameUiController?.isShoutoutOnCooldown(privateState));
}

function syncShoutoutTriggerState() {
  gameUiController?.syncShoutoutTriggerState();
}

function syncShoutoutUnlockTimer() {
  gameUiController?.syncShoutoutUnlockTimer();
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

function getGameScreenRoot() {
  return document.querySelector(".game-screen");
}

function getSeatAnchorFromDom(seat) {
  const root = getGameScreenRoot();
  const seatElement = root?.querySelector(`[data-motion-anchor="seat-seat-${seat}"]`);
  if (!root || !seatElement) {
    return null;
  }

  const rect = seatElement.getBoundingClientRect();
  if (rect.width === 0 && rect.height === 0) {
    return null;
  }

  return {
    x: rect.left + rect.width / 2,
    y: rect.top + rect.height / 2,
  };
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

function privateCards() {
  return gameUiController?.privateCards() || [];
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

function buildInviteLink() {
  const inviteUrl = new URL("/", window.location.origin);
  inviteUrl.searchParams.set("invite", state.inviteCode);
  return inviteUrl.toString();
}

function buildGameplayUiState(snapshot = state.snapshot?.data) {
  return deriveGameplayUiState({
    snapshot,
    privateState: state.privateState?.data,
    seat: state.seat,
    selectedCards: state.selectedCards,
    jokerRank: state.jokerRank,
    highLowChoice: state.highLowChoice,
  });
}

function buildViewportInputs() {
  return {
    viewportWidth: window.innerWidth || 390,
    viewportHeight: Math.max(window.innerHeight || 844, 1),
  };
}

function buildRulesMenuViewState(snapshot = state.snapshot?.data) {
  return {
    open: state.rulesMenuOpen,
    optionalTakePileEnabled: Boolean(snapshot?.rules?.allow_optional_take_pile),
  };
}

function buildShoutoutMenuViewState(snapshot = state.snapshot?.data) {
  return {
    open: state.shoutoutMenuOpen,
    canSendShoutouts: canSendShoutouts(snapshot),
    onCooldown: isShoutoutOnCooldown(),
    presets: shoutoutPresets(snapshot),
  };
}

function buildGameplayScreenViewState(
  snapshot = state.snapshot?.data,
  gameplayUi = buildGameplayUiState(snapshot),
) {
  const viewport = buildViewportInputs();
  return {
    localSeat: state.seat,
    errorMessage: state.error,
    selectedCardIds: state.selectedCards.map((card) => cardId(card)),
    jokerRank: state.jokerRank,
    highLowChoice: state.highLowChoice,
    hiddenLocalHandCardIds: [...state.hiddenLocalHandCardIds],
    turnNotice: {
      visible: state.turnNoticeVisible,
      headline: state.turnNoticeHeadline,
      copy: state.turnNoticeCopy,
    },
    animations: state.animations,
    turnArrivalSeat: state.turnArrivalSeat,
    presenceNow: state.presenceNow,
    kickSeatArmed: state.kickSeatArmed,
    handLayout: deriveHandLayout({
      cardCount: gameplayUi.privateCards.length,
      playerCount: snapshot.players.length,
      ...viewport,
    }),
    tableLayoutVariant: deriveTableLayoutVariant(viewport),
    shoutoutTrigger: shoutoutTriggerState(snapshot),
    rulesMenu: buildRulesMenuViewState(snapshot),
  };
}

function toggleCard(card) {
  gameUiController?.toggleCard(card);
}

function submitTakePile() {
  gameUiController?.submitTakePile();
}

function submitShoutout(shoutoutKey) {
  gameUiController?.submitShoutout(shoutoutKey);
}

function onSubmit(event) {
  const formElement =
    event.target instanceof HTMLFormElement ? event.target : null;
  if (!formElement || !app.contains(formElement)) {
    return;
  }
  event.preventDefault();
  state.error = "";
  const form = new FormData(formElement);
  const mode = formElement.dataset.mode;
  if (mode === "create") {
    sessionController.createGame(form).catch((error) => {
      state.error = error.message;
      render();
    });
  } else if (mode === "join") {
    sessionController.joinGame(form).catch((error) => {
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

function isMobileActiveGameLayout(snapshot = state.snapshot?.data) {
  return Boolean(snapshot);
}

function renderLanding() {
  return renderLandingView({
    landingJoinFirst: state.landingJoinFirst,
    landingOpenBucket: state.landingOpenBucket,
    landingInviteCode: state.landingInviteCode,
    showSavedSessionCard: hasSavedSession(),
    restoringSession: state.restoringSession,
    inviteCode: state.inviteCode,
    displayName: state.displayName,
    error: state.error,
    rulesMenuHtml: renderRulesMenuView(buildRulesMenuViewState()),
    escapeHtml,
  });
}

function renderGameTopbar(snapshot) {
  if (!snapshot) {
    resetLeaveConfirmation();
    return "";
  }
  return renderGameTopbarView({
    showCompactBrand: isMobileActiveGameLayout(snapshot),
    wsReady: state.wsReady,
    leaveArmed: state.leaveArmed,
  });
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

function renderShoutoutBubble(animation, snapshot, anchorOverride = null) {
  const player = snapshot?.players?.find(
    (entry) => entry.seat === animation.seat,
  );
  const anchor =
    anchorOverride ||
    resolveMotionAnchor(
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

function appendShoutoutBubble(animation) {
  if (!rememberShoutoutEvent(animation.eventId || "")) {
    return;
  }

  const snapshot = state.snapshot?.data;
  const motionLayer = ensureMotionLayer();
  const anchor = getSeatAnchorFromDom(animation.seat);
  if (!snapshot || !motionLayer || !anchor) {
    return;
  }

  const wrapper = document.createElement("div");
  wrapper.innerHTML = renderShoutoutBubble(animation, snapshot, anchor);
  const bubble = wrapper.firstElementChild;
  if (!bubble) {
    return;
  }

  motionLayer.appendChild(bubble);
  const duration = prefersReducedMotion() ? 320 : 1500;
  const timer = window.setTimeout(() => {
    bubble.remove();
    state.animationTimers = state.animationTimers.filter(
      (entry) => entry !== timer,
    );
  }, duration + 90);
  state.animationTimers = [...state.animationTimers, timer];
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

function renderApp(gameplayScreenView = null) {
  if (!state.snapshot) {
    return renderLanding();
  }

  const snapshot = state.snapshot.data;
  const screenView = gameplayScreenView
    ? gameplayScreenView
    : (() => {
        const gameplayUi = buildGameplayUiState(snapshot);
        return renderGameplayScreenView({
          snapshot,
          gameplayUi,
          viewState: buildGameplayScreenViewState(snapshot, gameplayUi),
        });
      })();

  return renderAppView({
    gameTopbarHtml: renderGameTopbar(snapshot),
    gameScreenClasses: screenView.gameScreenClasses,
    tableHtml: screenView.tableHtml,
    actionsHtml: screenView.actionsHtml,
    motionLayerHtml: renderMotionLayer(snapshot),
    globalErrorHtml:
      !isMobileActiveGameLayout(snapshot) && state.error
        ? `<section class="panel error">${escapeHtml(state.error)}</section>`
        : "",
  });
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
        state.handFanScrollLeft = handFan.scrollLeft;
        resetHandFanTouchState();
        const queuedRender = state.handDragQueuedRender;
        state.handDragQueuedRender = false;
        if (queuedRender) {
          render({ force: true });
        }
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

function closestAppTarget(event, selector) {
  const origin = event.target instanceof Element ? event.target : null;
  if (!origin) {
    return null;
  }
  const target = origin.closest(selector);
  if (!target || !app.contains(target)) {
    return null;
  }
  return target;
}

async function handleCopyInviteCodeClick() {
  try {
    await navigator.clipboard.writeText(state.inviteCode);
    state.error = "Invite code copied.";
  } catch (error) {
    state.error = "Copy failed. You can still share the code manually.";
  }
  render();
}

async function handleShareInviteClick() {
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
}

function onAppClick(event) {
  const cardButton = closestAppTarget(event, "[data-card-id]");
  if (cardButton) {
    if (Date.now() < state.suppressCardTapUntil) {
      return;
    }
    const card = privateCards().find(
      (entry) => cardId(entry) === cardButton.dataset.cardId,
    );
    if (card) {
      toggleCard(card);
    }
    return;
  }

  const handPrimaryAction = closestAppTarget(event, "#hand-primary-action");
  if (handPrimaryAction) {
    gameUiController?.submitPrimaryAction(
      handPrimaryAction.dataset.primaryAction || "",
    );
    return;
  }

  if (closestAppTarget(event, "#take-pile-overlay")) {
    submitTakePile();
    return;
  }

  const jokerRankButton = closestAppTarget(event, "[data-joker-rank]");
  if (jokerRankButton) {
    gameUiController?.setJokerRank(jokerRankButton.dataset.jokerRank);
    return;
  }

  if (closestAppTarget(event, "#choose-higher")) {
    gameUiController?.setHighLowChoice("HIGHER");
    return;
  }

  if (closestAppTarget(event, "#choose-lower")) {
    gameUiController?.setHighLowChoice("LOWER");
    return;
  }

  if (closestAppTarget(event, "#start-game")) {
    sessionController.startGame();
    return;
  }

  if (closestAppTarget(event, "#rematch-game")) {
    sessionController.rematchGame();
    return;
  }

  if (closestAppTarget(event, "#copy-invite-code")) {
    void handleCopyInviteCodeClick();
    return;
  }

  if (closestAppTarget(event, "#restore-session")) {
    sessionController.restoreSession({ resetRetry: true });
    return;
  }

  const landingBucketButton = closestAppTarget(event, "[data-landing-bucket]");
  if (landingBucketButton) {
    toggleLandingBucket(landingBucketButton.dataset.landingBucket);
    return;
  }

  if (closestAppTarget(event, "#forget-session")) {
    forgetSavedSession();
    return;
  }

  if (closestAppTarget(event, "#share-invite")) {
    void handleShareInviteClick();
    return;
  }

  const optionalTakeToggle = closestAppTarget(event, "#toggle-optional-take-pile");
  if (optionalTakeToggle) {
    sessionController.updateGameSettings(
      optionalTakeToggle.getAttribute("aria-checked") !== "true",
    );
    return;
  }

  const kickSeatButton = closestAppTarget(event, "[data-kick-seat]");
  if (kickSeatButton) {
    handleKickSeatClick(Number(kickSeatButton.dataset.kickSeat));
    return;
  }

  if (closestAppTarget(event, "#open-rules-menu")) {
    openRulesMenu();
    return;
  }

  if (closestAppTarget(event, "#open-shoutout-menu")) {
    toggleShoutoutMenu();
    return;
  }

  if (
    closestAppTarget(event, "#close-rules-menu") ||
    closestAppTarget(event, "#close-rules-menu-backdrop")
  ) {
    closeRulesMenu();
    return;
  }

  if (
    closestAppTarget(event, "#close-shoutout-menu") ||
    closestAppTarget(event, "#close-shoutout-menu-backdrop")
  ) {
    closeShoutoutMenu({ rerender: false });
    return;
  }

  const shoutoutChip = closestAppTarget(event, "[data-shoutout-key]");
  if (shoutoutChip) {
    submitShoutout(shoutoutChip.dataset.shoutoutKey || "");
    return;
  }

  if (closestAppTarget(event, "#leave-game")) {
    clearSession();
    return;
  }

  if (closestAppTarget(event, "#leave-game-header")) {
    handleLeaveClick();
  }
}

function wireDelegatedAppEvents() {
  if (appDelegatedEventsWired) {
    return;
  }
  app.addEventListener("click", onAppClick);
  app.addEventListener("submit", onSubmit);
  appDelegatedEventsWired = true;
}

function wireEvents() {
  wireDelegatedAppEvents();
  const handFan = app.querySelector(".hand-fan");
  if (!handFan || handFan.dataset.wired === "true") {
    return;
  }
  handFan.dataset.wired = "true";
  wireHandFanInteractions(handFan);
}

function captureHandFanScrollBeforeRender() {
  if (state.snapshot?.data?.status !== "IN_GAME") {
    return;
  }
  const handFan = app.querySelector(".hand-fan");
  if (!handFan) {
    return;
  }
  state.handFanScrollLeft = handFan.scrollLeft;
}

function render({ force = false } = {}) {
  const snapshot = state.snapshot?.data || null;
  captureHandFanScrollBeforeRender();
  if (!force && isHandInteractionActive()) {
    const handFan = app.querySelector(".hand-fan");
    if (handFan) {
      state.handFanScrollLeft = handFan.scrollLeft;
    }
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
    Boolean(snapshot) && snapshot.status !== "LOBBY",
  );
  syncPresenceTicker();
  syncShoutoutUnlockTimer();
  const gameplayUi = snapshot ? buildGameplayUiState(snapshot) : null;
  const gameplayScreenView = snapshot
    ? renderGameplayScreenView({
        snapshot,
        gameplayUi,
        viewState: buildGameplayScreenViewState(snapshot, gameplayUi),
      })
    : null;
  app.innerHTML = renderApp(gameplayScreenView);
  if (!state.snapshot && state.pendingLandingNameFocus) {
    const joinNameInput = document.getElementById("join-name");
    if (joinNameInput) {
      joinNameInput.focus();
      state.pendingLandingNameFocus = false;
    }
  }
  if (!document.getElementById("leave-game-header")) {
    resetLeaveConfirmation();
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
  syncShoutoutMenu(snapshot ? buildShoutoutMenuViewState(snapshot) : null);
}

gameUiController = createGameUiController({
  render,
  shoutoutCooldownMs,
  closeShoutoutMenu,
  detectAnimationEvents,
  clearMotionState,
  resetLeaveConfirmation,
  resetKickSeatConfirmation,
  captureLocalPlaySelection,
  buildLocalPlayThrowMotions,
  prefersReducedMotion,
  queueLocalMotion,
});

sessionController = createSessionController({
  appendShoutoutBubble,
  clearMotionState,
  clearSession,
  gameUiController,
  render,
});
gameUiController.bindSessionController(sessionController);

loadStoredSession();
loadInviteLink();
render();
sessionController.restoreSession();

window.addEventListener("pageshow", () => {
  sessionController.attemptSessionRecovery({ resetRetry: true });
});

window.addEventListener("focus", () => {
  sessionController.attemptSessionRecovery({ resetRetry: true });
});

window.addEventListener("online", () => {
  sessionController.attemptSessionRecovery({ resetRetry: true });
});

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") {
    sessionController.attemptSessionRecovery({ resetRetry: true });
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
    const handFan = app.querySelector(".hand-fan");
    if (handFan) {
      state.handFanScrollLeft = handFan.scrollLeft;
    }
    render();
  }
});

window.addEventListener("orientationchange", () => {
  if (state.snapshot) {
    const handFan = app.querySelector(".hand-fan");
    if (handFan) {
      state.handFanScrollLeft = handFan.scrollLeft;
    }
    render();
  }
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker
    .register("/static/sw.js?v=20260405b")
    .then(() => {
      if (navigator.serviceWorker.controller) {
        navigator.serviceWorker.addEventListener("controllerchange", () => {
          window.location.reload();
        });
      }
    })
    .catch(() => {});
}
