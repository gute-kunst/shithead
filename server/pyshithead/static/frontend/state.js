const storageKey = "shithead.alpha.session";

export const state = {
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
  shoutoutExpiryTimer: null,
  rulesMenuOpen: false,
  shoutoutMenuOpen: false,
  shoutoutComposerOpen: false,
  shoutoutComposerText: "",
  shoutoutComposerEmoji: "",
  shoutoutComposerError: "",
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
  shoutoutRecords: [],
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

export function loadStoredSession() {
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

export function persistSession() {
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

export function hasSavedSession() {
  return Boolean(state.inviteCode && state.playerToken);
}

export function clearReconnectTimer() {
  if (state.reconnectTimer !== null) {
    window.clearTimeout(state.reconnectTimer);
    state.reconnectTimer = null;
  }
}

export function clearLeaveConfirmTimer() {
  if (state.leaveConfirmTimer !== null) {
    window.clearTimeout(state.leaveConfirmTimer);
    state.leaveConfirmTimer = null;
  }
}

export function clearKickSeatConfirmTimer() {
  if (state.kickSeatConfirmTimer !== null) {
    window.clearTimeout(state.kickSeatConfirmTimer);
    state.kickSeatConfirmTimer = null;
  }
}

export function clearPresenceTicker() {
  if (state.presenceTicker !== null) {
    window.clearInterval(state.presenceTicker);
    state.presenceTicker = null;
  }
}

export function clearShoutoutUnlockTimer() {
  if (state.shoutoutUnlockTimer !== null) {
    window.clearTimeout(state.shoutoutUnlockTimer);
    state.shoutoutUnlockTimer = null;
  }
}

export function clearShoutoutExpiryTimer() {
  if (state.shoutoutExpiryTimer !== null) {
    window.clearTimeout(state.shoutoutExpiryTimer);
    state.shoutoutExpiryTimer = null;
  }
}

export function clearShoutoutState() {
  clearShoutoutUnlockTimer();
  clearShoutoutExpiryTimer();
  state.shoutoutMenuOpen = false;
  state.shoutoutComposerOpen = false;
  state.shoutoutComposerText = "";
  state.shoutoutComposerEmoji = "";
  state.shoutoutComposerError = "";
  state.shoutoutRecords = [];
  state.seenShoutoutEvents = [];
}

export function resetHandFanTouchState() {
  state.handTouchActiveId = null;
  state.handTouchStartX = 0;
  state.handTouchStartY = 0;
  state.handTouchStartScrollLeft = 0;
  state.handTouchStartAt = 0;
  state.handTouchMoved = false;
}

export function isHandDragActive() {
  return state.handDragActiveInputId !== null;
}

export function isHandInteractionActive() {
  return isHandDragActive() || state.handTouchActiveId !== null;
}

export function clearTurnNoticeTimer() {
  if (state.turnNoticeTimer !== null) {
    window.clearTimeout(state.turnNoticeTimer);
    state.turnNoticeTimer = null;
  }
}

export function clearAnimationTimers() {
  state.animationTimers.forEach((timer) => window.clearTimeout(timer));
  state.animationTimers = [];
}

export function clearTurnArrivalTimer() {
  if (state.turnArrivalTimer !== null) {
    window.clearTimeout(state.turnArrivalTimer);
    state.turnArrivalTimer = null;
  }
}

export function clearLocalPlaySendTimer() {
  if (state.localPlaySendTimer !== null) {
    window.clearTimeout(state.localPlaySendTimer);
    state.localPlaySendTimer = null;
  }
}

export function clearPendingLocalPlay() {
  clearLocalPlaySendTimer();
  state.pendingLocalPlay = null;
  state.hiddenLocalHandCardIds = [];
}

export function clearRestoreRetryTimer() {
  if (state.restoreRetryTimer !== null) {
    window.clearTimeout(state.restoreRetryTimer);
    state.restoreRetryTimer = null;
  }
}

export function resetSelection() {
  state.selectedCards = [];
  state.highLowChoice = "";
  state.jokerRank = null;
}
