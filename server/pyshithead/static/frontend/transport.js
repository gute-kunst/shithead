import { state } from "./state.js";

const shoutoutSeenWindowMs = 12000;
const shoutoutHistoryLimitPerSeat = 1;

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
  const previousVisibleSignature = state.shoutoutRecords
    .filter((record) => (record?.expiresAt || 0) > now)
    .map((record) => record.id)
    .join("|");
  const historyRecordsBySeat = state.shoutoutRecords.reduce((recordsBySeat, record) => {
    if (!record?.historyEligible || !Number.isInteger(record?.seat)) {
      return recordsBySeat;
    }
    const seatRecords = recordsBySeat.get(record.seat) || [];
    seatRecords.push(record);
    recordsBySeat.set(record.seat, seatRecords);
    return recordsBySeat;
  }, new Map());

  const retainedHistoryIds = new Set();
  historyRecordsBySeat.forEach((records) => {
    records
      .slice()
      .sort((left, right) => (right.createdAt || 0) - (left.createdAt || 0))
      .slice(0, shoutoutHistoryLimitPerSeat)
      .forEach((record) => {
        retainedHistoryIds.add(record.id);
      });
  });

  const retainedRecords = state.shoutoutRecords.filter((record) => {
    if ((record?.expiresAt || 0) > now) {
      return true;
    }
    if (!record?.historyEligible) {
      return false;
    }
    return retainedHistoryIds.has(record.id);
  });
  const nextVisibleSignature = retainedRecords
    .filter((record) => (record?.expiresAt || 0) > now)
    .map((record) => record.id)
    .join("|");
  if (
    retainedRecords.length === state.shoutoutRecords.length &&
    previousVisibleSignature === nextVisibleSignature
  ) {
    return false;
  }
  state.shoutoutRecords = retainedRecords;
  return true;
}

export function applyShoutoutEvent(payload, { now = Date.now() } = {}) {
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

  const data = payload?.data || {};
  const preset = data.preset || {};
  const source = data.source || (preset.key ? "preset" : "custom");
  const durationMs = Math.max(0, Number(data.duration_ms) || 1500);
  const shoutoutRecord = {
    id: eventId || `local-${now}-${state.shoutoutRecords.length + 1}`,
    eventId,
    seat: data.seat,
    source,
    presetKey: preset.key || "",
    text: data.text || preset.label || "Shoutout",
    emoji: data.emoji || (source === "preset" ? preset.emoji || "✨" : ""),
    accentColor: data.accent_color || preset.color || "#f4b942",
    durationMs,
    createdAt: now,
    expiresAt: now + durationMs,
    historyEligible: data.history_eligible !== false,
  };

  state.shoutoutRecords = [...state.shoutoutRecords, shoutoutRecord];
  pruneExpiredShoutouts(now);
  return {
    applied: true,
    shoutoutRecord,
  };
}
