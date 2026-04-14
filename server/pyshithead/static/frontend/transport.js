import { state } from "./state.js";

const shoutoutSeenWindowMs = 12000;

export function applySessionSnapshot(payload, { touchPresence = false } = {}) {
  const previousSnapshot = state.snapshot?.data || null;
  state.snapshot = payload;
  if (touchPresence) {
    state.presenceNow = Date.now();
  }
  return {
    previousSnapshot,
    snapshot: payload?.data || null,
  };
}

export function applyPrivateState(payload) {
  const previousPrivateState = state.privateState?.data || null;
  const previousPrivateCards = previousPrivateState?.private_cards || [];
  state.privateState = payload;
  return {
    previousPrivateState,
    previousPrivateCards,
    privateState: payload?.data || null,
  };
}

export function applyServerError(message) {
  state.error = message;
}

function pruneSeenShoutoutEvents(now = Date.now()) {
  state.seenShoutoutEvents = state.seenShoutoutEvents.filter(
    (entry) => now - entry.seenAt <= shoutoutSeenWindowMs,
  );
}

export function pruneExpiredShoutouts(now = Date.now()) {
  const visibleRecords = state.shoutoutRecords.filter(
    (record) => record.expiresAt > now,
  );
  if (visibleRecords.length === state.shoutoutRecords.length) {
    return false;
  }
  state.shoutoutRecords = visibleRecords;
  return true;
}

export function applyShoutoutEvent(
  payload,
  { durationMs = 1500, now = Date.now() } = {},
) {
  pruneSeenShoutoutEvents(now);
  pruneExpiredShoutouts(now);

  const eventId = payload?.data?.event_id || "";
  if (
    eventId &&
    state.seenShoutoutEvents.some((entry) => entry.eventId === eventId)
  ) {
    return { applied: false, shoutoutRecord: null };
  }

  if (eventId) {
    state.seenShoutoutEvents = [
      ...state.seenShoutoutEvents,
      { eventId, seenAt: now },
    ].slice(-24);
  }

  const preset = payload?.data?.preset || {};
  const shoutoutRecord = {
    id: eventId || `local-${now}-${state.shoutoutRecords.length + 1}`,
    eventId,
    seat: payload?.data?.seat,
    source: "preset",
    presetKey: preset.key || "",
    text: preset.label || "Shoutout",
    emoji: preset.emoji || "✨",
    accentColor: preset.color || "#f4b942",
    durationMs,
    createdAt: now,
    expiresAt: now + durationMs,
  };

  state.shoutoutRecords = [...state.shoutoutRecords, shoutoutRecord];
  return {
    applied: true,
    shoutoutRecord,
  };
}
