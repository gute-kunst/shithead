import {
  clearPendingLocalPlay,
  clearShoutoutExpiryTimer,
  clearShoutoutUnlockTimer,
  clearTurnNoticeTimer,
  resetSelection,
  state,
} from "./state.js";
import { applyShoutoutEvent, pruneExpiredShoutouts } from "./transport.js";
import {
  canChoosePublicCards as deriveCanChoosePublicCards,
  deriveGameplayUiState,
  GAMEPLAY_PRIMARY_ACTIONS,
  getJokerOptions,
  getPendingJokerCard,
  getPlayRank,
  getSelectedHasJoker,
  getSelectedNonJokerRank,
  hasHighLowChoice,
  hasPendingJokerSelection as deriveHasPendingJokerSelection,
  isJokerCard,
  JOKER_ALLOWED_RANKS,
} from "./gameplay_ui_state.js";

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

export function createGameUiController({
  render,
  shoutoutCooldownMs,
  shoutoutDisplayDurationMs,
  closeShoutoutMenu,
  syncShoutoutView,
  detectAnimationEvents,
  clearMotionState,
  resetLeaveConfirmation,
  resetKickSeatConfirmation,
  captureLocalPlaySelection,
  buildLocalPlayThrowMotions,
  prefersReducedMotion,
  queueLocalMotion,
}) {
  let sessionController = null;

  function bindSessionController(controller) {
    sessionController = controller;
  }

  function canHostRemovePlayer(player, snapshot = state.snapshot?.data) {
    const self =
      snapshot?.players?.find((entry) => entry.seat === state.seat) || null;
    return Boolean(
      self && self.is_host && !player.is_host && !player.is_connected,
    );
  }

  function syncKickSeatConfirmation(snapshot = state.snapshot?.data) {
    if (!Number.isInteger(state.kickSeatArmed)) {
      return;
    }
    const armedPlayer = snapshot?.players?.find(
      (player) => player.seat === state.kickSeatArmed,
    );
    if (!armedPlayer || !canHostRemovePlayer(armedPlayer, snapshot)) {
      resetKickSeatConfirmation();
    }
  }

  function currentGameState() {
    return state.snapshot?.data?.game_state || null;
  }

  function isMyTurn(snapshot = state.snapshot?.data) {
    return snapshot?.current_turn_seat === state.seat;
  }

  function privateCards() {
    return state.privateState?.data?.private_cards || [];
  }

  function selectedNonJokerRank() {
    return getSelectedNonJokerRank(state.selectedCards);
  }

  function selectedHasJoker() {
    return getSelectedHasJoker(state.selectedCards);
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

  function playRank() {
    return getPlayRank({
      selectedCards: state.selectedCards,
      jokerRank: state.jokerRank,
    });
  }

  function canChoosePublicCards() {
    return deriveCanChoosePublicCards({
      snapshot: state.snapshot?.data,
      privateState: state.privateState?.data,
      seat: state.seat,
    });
  }

  function pendingJokerCard() {
    return getPendingJokerCard({ privateState: state.privateState?.data });
  }

  function hasPendingJokerSelection() {
    return deriveHasPendingJokerSelection({
      privateState: state.privateState?.data,
    });
  }

  function jokerOptions(
    snapshot = state.snapshot?.data,
    cards = state.selectedCards,
  ) {
    return getJokerOptions({ snapshot, cards });
  }

  function deriveCurrentGameplayUi(
    snapshot = state.snapshot?.data,
    privateState = state.privateState?.data,
  ) {
    return deriveGameplayUiState({
      snapshot,
      privateState,
      seat: state.seat,
      selectedCards: state.selectedCards,
      jokerRank: state.jokerRank,
      highLowChoice: state.highLowChoice,
    });
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

  function syncTurnNotice(snapshot, { suppress = false } = {}) {
    if (!snapshot) {
      hideTurnNotice();
      state.lastTurnNoticeKey = "";
      return;
    }

    const notice = deriveCurrentGameplayUi(snapshot).turnNotice;
    const hasChanged = notice.key !== state.lastTurnNoticeKey;
    state.lastTurnNoticeKey = notice.key;

    if (suppress) {
      state.turnNoticeVisible = false;
      return;
    }

    if (hasChanged) {
      showTurnNotice(notice.headline, notice.copy);
    }
  }

  function clearTurnNoticeState() {
    hideTurnNotice();
    state.lastTurnNoticeKey = "";
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

  function canSendShoutouts(snapshot = state.snapshot?.data) {
    return Boolean(
      snapshot &&
        state.wsReady &&
        (snapshot.status === "LOBBY" ||
          snapshot.status === "IN_GAME" ||
          snapshot.status === "GAME_OVER"),
    );
  }

  function shoutoutPresets(snapshot = state.snapshot?.data) {
    return snapshot?.shoutout_presets || [];
  }

  function shoutoutCustomConfig(snapshot = state.snapshot?.data) {
    return (
      snapshot?.shoutout_custom_config || {
        max_text_length: 50,
        emoji_options: [],
      }
    );
  }

  function resetShoutoutComposer() {
    state.shoutoutComposerOpen = false;
    state.shoutoutComposerText = "";
    state.shoutoutComposerEmoji = "";
    state.shoutoutComposerError = "";
  }

  function closeManagedShoutoutMenu({ rerender = false } = {}) {
    resetShoutoutComposer();
    closeShoutoutMenu({ rerender });
  }

  function focusCustomShoutoutComposer() {
    window.setTimeout(() => {
      document.getElementById("custom-shoutout-text")?.focus();
    }, 0);
  }

  function syncShoutoutTriggerState() {
    const shoutoutButton = document.getElementById("open-shoutout-menu");
    if (!shoutoutButton) {
      return;
    }

    const {
      shoutoutReady,
      shoutoutCooldown,
      shoutoutLocked,
      shoutoutEnabled,
      shoutoutFillStyle,
    } = shoutoutTriggerState();
    shoutoutButton.className = `table-shoutout-trigger ${
      shoutoutEnabled ? "" : "disabled"
    } ${shoutoutLocked ? "locked" : ""}`.trim();
    shoutoutButton.disabled = !shoutoutEnabled;
    shoutoutButton.title = !shoutoutReady
      ? "Connecting to the table"
      : shoutoutLocked
        ? `Shoutouts available in ${Math.max(
            1,
            Math.ceil(shoutoutCooldown.remainingMs / 1000),
          )}s`
        : "Shoutouts";
    shoutoutButton.style.cssText = shoutoutFillStyle;
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

  function syncVisibleShoutoutTimer() {
    clearShoutoutExpiryTimer();
    const now = Date.now();
    const activeShoutouts = state.shoutoutRecords.filter(
      (record) => (record.expiresAt || 0) > now,
    );
    if (activeShoutouts.length === 0) {
      return;
    }
    const nextExpiryAt = Math.min(
      ...activeShoutouts.map((record) => record.expiresAt || 0),
    );
    if (!Number.isFinite(nextExpiryAt) || nextExpiryAt <= 0) {
      return;
    }
    state.shoutoutExpiryTimer = window.setTimeout(() => {
      state.shoutoutExpiryTimer = null;
      pruneExpiredShoutouts();
      syncShoutoutView();
      syncVisibleShoutoutTimer();
    }, Math.max(0, nextExpiryAt - Date.now()) + 30);
  }

  function shoutoutTriggerState(
    snapshot = state.snapshot?.data,
    privateState = state.privateState?.data,
  ) {
    const shoutoutReady = canSendShoutouts(snapshot);
    const shoutoutCooldown = shoutoutCooldownState(privateState);
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
    return {
      shoutoutReady,
      shoutoutCooldown,
      shoutoutLocked,
      shoutoutEnabled,
      shoutoutFillStyle,
    };
  }

  function buildVisibleShoutoutsBySeat(
    snapshot = state.snapshot?.data,
    now = Date.now(),
  ) {
    pruneExpiredShoutouts(now);
    const validSeats = new Set((snapshot?.players || []).map((player) => player.seat));
    return state.shoutoutRecords.reduce((recordsBySeat, record) => {
      if (!validSeats.has(record.seat) || (record.expiresAt || 0) <= now) {
        return recordsBySeat;
      }
      const currentSeatRecords = recordsBySeat[record.seat] || [];
      recordsBySeat[record.seat] = [...currentSeatRecords, record];
      return recordsBySeat;
    }, {});
  }

  function buildSavedShoutoutsBySeat(
    snapshot = state.snapshot?.data,
    now = Date.now(),
  ) {
    pruneExpiredShoutouts(now);
    const validSeats = new Set((snapshot?.players || []).map((player) => player.seat));
    return state.shoutoutRecords.reduce((recordsBySeat, record) => {
      if (
        !validSeats.has(record.seat) ||
        !record.historyEligible ||
        (record.expiresAt || 0) > now
      ) {
        return recordsBySeat;
      }
      const currentSeatRecord = recordsBySeat[record.seat] || null;
      if (!currentSeatRecord || (record.createdAt || 0) > (currentSeatRecord.createdAt || 0)) {
        recordsBySeat[record.seat] = record;
      }
      return recordsBySeat;
    }, {});
  }

  function buildShoutoutMenuViewState(snapshot = state.snapshot?.data) {
    const customConfig = shoutoutCustomConfig(snapshot);
    return {
      open: state.shoutoutMenuOpen,
      canSendShoutouts: canSendShoutouts(snapshot),
      onCooldown: isShoutoutOnCooldown(),
      presets: shoutoutPresets(snapshot),
      composer: {
        open: state.shoutoutComposerOpen,
        text: state.shoutoutComposerText,
        emoji: state.shoutoutComposerEmoji,
        error: state.shoutoutComposerError,
        maxTextLength: customConfig.max_text_length || 50,
        emojiOptions: customConfig.emoji_options || [],
      },
    };
  }

  function buildShoutoutRenderViewState(snapshot = state.snapshot?.data) {
    if (!snapshot) {
      return null;
    }
    const now = Date.now();
    return {
      localSeat: state.seat,
      shoutoutMenu: buildShoutoutMenuViewState(snapshot),
      visibleShoutoutsBySeat: buildVisibleShoutoutsBySeat(snapshot, now),
      savedShoutoutsBySeat: buildSavedShoutoutsBySeat(snapshot, now),
    };
  }

  function openCustomShoutoutComposer() {
    state.shoutoutComposerOpen = true;
    state.shoutoutComposerError = "";
    syncShoutoutView();
    focusCustomShoutoutComposer();
  }

  function closeCustomShoutoutComposer() {
    resetShoutoutComposer();
    syncShoutoutView();
  }

  function setCustomShoutoutText(text) {
    const maxTextLength = Math.max(
      1,
      Number(shoutoutCustomConfig().max_text_length) || 50,
    );
    state.shoutoutComposerText = String(text || "").slice(0, maxTextLength);
    if (state.shoutoutComposerError) {
      state.shoutoutComposerError = "";
      syncShoutoutView();
      focusCustomShoutoutComposer();
    }
  }

  function toggleCustomShoutoutEmoji(emoji) {
    const options = new Set(
      (shoutoutCustomConfig().emoji_options || []).map((option) => option.value),
    );
    if (!options.has(emoji)) {
      return;
    }
    state.shoutoutComposerEmoji =
      state.shoutoutComposerEmoji === emoji ? "" : emoji;
    state.shoutoutComposerError = "";
    syncShoutoutView();
    focusCustomShoutoutComposer();
  }

  function submitCustomShoutout() {
    const text = state.shoutoutComposerText.trim();
    const emoji = state.shoutoutComposerEmoji || "";
    if (!text) {
      state.shoutoutComposerError = "Enter a short shoutout first.";
      syncShoutoutView();
      focusCustomShoutoutComposer();
      return;
    }
    state.error = "";
    const sent = sendAction({
      type: "send_shoutout",
      shoutout_text: text,
      shoutout_emoji: emoji,
    });
    if (!sent) {
      return;
    }
    resetShoutoutComposer();
    closeShoutoutMenu({ rerender: false });
    primeLocalShoutoutCooldown();
    syncShoutoutTriggerState();
    syncShoutoutUnlockTimer();
  }

  function replaySavedShoutout(seat) {
    const savedShoutout = buildSavedShoutoutsBySeat()[seat] || null;
    if (!savedShoutout) {
      return;
    }
    state.shoutoutMenuOpen = false;
    resetShoutoutComposer();
    const now = Date.now();
    state.shoutoutRecords = [
      ...state.shoutoutRecords,
      {
        ...savedShoutout,
        id: `replay-${seat}-${now}`,
        eventId: "",
        createdAt: now,
        expiresAt: now + Math.max(0, savedShoutout.durationMs || 1500),
        historyEligible: false,
      },
    ];
    pruneExpiredShoutouts(now);
    syncVisibleShoutoutTimer();
    syncShoutoutView();
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

  function sendAction(payload) {
    return sessionController?.sendAction(payload) || false;
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
      sendAction(payload);
      resetSelection();
      return;
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
        if (
          nonJokerRank !== null &&
          !JOKER_ALLOWED_RANKS.includes(nonJokerRank)
        ) {
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
        if (!JOKER_ALLOWED_RANKS.includes(card.rank)) {
          state.error = "Jokers cannot be 2, 5, or 10.";
          render();
          return;
        }
        state.selectedCards = [...state.selectedCards, card];
        state.error = "";
        syncJokerSelection();
      } else if (state.selectedCards.length === 0 || nonJokerRank === card.rank) {
        if (selectedHasJoker() && !JOKER_ALLOWED_RANKS.includes(card.rank)) {
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

  function setJokerRank(rank) {
    state.jokerRank = Number(rank);
    if (state.jokerRank !== state.snapshot?.data?.rules.high_low_rank) {
      state.highLowChoice = "";
    }
    state.error = "";
    render();
  }

  function setHighLowChoice(choice) {
    state.highLowChoice = hasHighLowChoice(choice) ? choice : "";
    state.error = "";
    render();
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
    const gameplayUi = deriveCurrentGameplayUi();
    if (state.localPlaySendTimer !== null) {
      return;
    }
    if (gameplayUi.selectedPlay.selectedCards.length === 0) {
      state.error = "Select at least one card.";
      render();
      return;
    }
    if (gameplayUi.selectedPlay.needsJokerRankChoice) {
      state.error = "Choose what the joker should be first.";
      render();
      return;
    }
    if (gameplayUi.selectedPlay.needsHighLowChoice) {
      state.error =
        "Choose whether the next player must go higher or may go lower.";
      render();
      return;
    }
    const payload = {
      type: "play_private_cards",
      cards: [...gameplayUi.selectedPlay.selectedCards],
      choice:
        gameplayUi.selectedPlay.currentPlayRank ===
        state.snapshot.data.rules.high_low_rank
          ? state.highLowChoice
          : "",
      joker_rank: gameplayUi.selectedPlay.selectedHasJoker ? state.jokerRank : null,
    };
    const capturedCards = captureLocalPlaySelection();
    const shouldStageLocalThrow =
      !prefersReducedMotion() &&
      Array.isArray(capturedCards) &&
      capturedCards.length > 0;
    const throwCards = shouldStageLocalThrow
      ? buildLocalPlayThrowMotions(capturedCards)
      : [];
    sendPlayPrivateCards(payload, {
      stageOptimistic: shouldStageLocalThrow,
      throwCards,
      capturedCards: Array.isArray(capturedCards) ? capturedCards : [],
    });
  }

  function submitTakePile() {
    sendAction({ type: "take_play_pile" });
  }

  function submitShoutout(shoutoutKey) {
    if (!shoutoutKey) {
      return;
    }
    closeManagedShoutoutMenu({ rerender: false });
    state.error = "";
    const sent = sendAction({
      type: "send_shoutout",
      shoutout_key: shoutoutKey,
    });
    if (!sent) {
      return;
    }
    primeLocalShoutoutCooldown();
    syncShoutoutTriggerState();
    syncShoutoutUnlockTimer();
  }

  function applyRealtimeShoutout(payload) {
    const outcome = applyShoutoutEvent(payload);
    if (!outcome.applied) {
      return;
    }
    syncVisibleShoutoutTimer();
    syncShoutoutView();
  }

  function expireVisibleShoutouts() {
    pruneExpiredShoutouts(Date.now());
    syncShoutoutView();
    syncVisibleShoutoutTimer();
  }

  function submitHiddenCard() {
    sendAction({ type: "play_hidden_card" });
  }

  function submitResolveJoker() {
    const gameplayUi = deriveCurrentGameplayUi();
    if (!gameplayUi.pendingJoker.active) {
      state.error = "No joker is waiting to be resolved.";
      render();
      return;
    }
    if (gameplayUi.selectedPlay.needsJokerRankChoice) {
      state.error = "Choose what the joker should be first.";
      render();
      return;
    }
    if (gameplayUi.selectedPlay.needsHighLowChoice) {
      state.error =
        "Choose whether the next player must go higher or may go lower.";
      render();
      return;
    }

    const choice = gameplayUi.pendingJoker.isRevealedJoker
      ? gameplayUi.selectedPlay.currentPlayRank ===
          state.snapshot.data.rules.high_low_rank
        ? state.highLowChoice
        : ""
      : state.highLowChoice;

    sendAction({
      type: "resolve_joker",
      choice,
      joker_rank: gameplayUi.pendingJoker.isRevealedJoker ? state.jokerRank : null,
    });
    resetSelection();
  }

  const primaryActionHandlers = Object.freeze({
    [GAMEPLAY_PRIMARY_ACTIONS.CHOOSE_PUBLIC_CARDS]: submitChoosePublicCards,
    [GAMEPLAY_PRIMARY_ACTIONS.PLAY_PRIVATE_CARDS]: submitPlayCards,
    [GAMEPLAY_PRIMARY_ACTIONS.PLAY_HIDDEN_CARD]: submitHiddenCard,
    [GAMEPLAY_PRIMARY_ACTIONS.RESOLVE_JOKER]: submitResolveJoker,
  });

  function submitPrimaryAction(actionId) {
    const handler = primaryActionHandlers[actionId];
    if (handler) {
      handler();
    }
  }

  function onAuthPayloadApplied(snapshot) {
    syncKickSeatConfirmation(snapshot);
    syncTurnNotice(snapshot, { suppress: true });
  }

  function onRealtimeSessionSnapshotApplied(previousSnapshot, snapshot) {
    detectAnimationEvents(previousSnapshot, snapshot);
    syncKickSeatConfirmation(snapshot);
    syncTurnNotice(snapshot);
    if (snapshot.status === "LOBBY" && previousSnapshot?.status === "GAME_OVER") {
      clearGameStateForLobby();
    }
    if (snapshot.status === "GAME_OVER" || !isMyTurn(snapshot)) {
      resetSelection();
    }
  }

  function onRealtimePrivateStateApplied({
    previousPrivateState,
    previousPrivateCards,
    privateState,
  }) {
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
      closeManagedShoutoutMenu({ rerender: false });
    }
    if (isShoutoutCooldownOnlyUpdate(previousPrivateState, privateState)) {
      syncShoutoutTriggerState();
      syncShoutoutUnlockTimer();
      return { skipRender: true };
    }
    if (privateState?.pending_joker_selection || privateState?.pending_hidden_take) {
      state.selectedCards = [];
      state.jokerRank = privateState?.pending_joker_card?.effective_rank || null;
      state.highLowChoice = "";
    }
    return { skipRender: false };
  }

  function onActionError() {
    clearPendingLocalPlay();
    state.pendingLocalDrawAnimation = null;
  }

  function onActionSnapshotApplied(
    previousSnapshot,
    snapshot,
    { detectAnimations = false } = {},
  ) {
    if (detectAnimations) {
      detectAnimationEvents(previousSnapshot, snapshot);
    }
  }

  return {
    applyRealtimeShoutout,
    bindSessionController,
    buildShoutoutRenderViewState,
    canChoosePublicCards,
    canSendShoutouts,
    clearGameStateForLobby,
    closeCustomShoutoutComposer,
    clearTurnNoticeState,
    currentGameState,
    expireVisibleShoutouts,
    hasPendingJokerSelection,
    isMyTurn,
    isShoutoutOnCooldown,
    jokerOptions,
    onActionError,
    onActionSnapshotApplied,
    onAuthPayloadApplied,
    onRealtimePrivateStateApplied,
    onRealtimeSessionSnapshotApplied,
    pendingJokerCard,
    playRank,
    privateCards,
    replaySavedShoutout,
    resetKickSeatConfirmation,
    selectedHasJoker,
    setCustomShoutoutText,
    setHighLowChoice,
    setJokerRank,
    openCustomShoutoutComposer,
    shoutoutTriggerState,
    submitCustomShoutout,
    submitChoosePublicCards,
    submitHiddenCard,
    submitPlayCards,
    submitPrimaryAction,
    submitResolveJoker,
    submitShoutout,
    submitTakePile,
    syncKickSeatConfirmation,
    syncShoutoutTriggerState,
    syncShoutoutUnlockTimer,
    syncVisibleShoutoutTimer,
    syncTurnNotice,
    toggleCustomShoutoutEmoji,
    toggleCard,
  };
}
