export const JOKER_RANK = 15;
export const GAMEPLAY_PRIMARY_ACTIONS = Object.freeze({
  CHOOSE_PUBLIC_CARDS: "choose-public-cards",
  PLAY_PRIVATE_CARDS: "play-private-cards",
  PLAY_HIDDEN_CARD: "play-hidden-card",
  RESOLVE_JOKER: "resolve-joker",
});
export const JOKER_ALLOWED_RANKS = [3, 4, 6, 7, 8, 9, 11, 13, 12, 14];
export const JOKER_SYMBOL = "★";

export function isJokerCard(card) {
  return Boolean(card && (card.is_joker || card.rank === JOKER_RANK));
}

export function cardEffectiveRank(card) {
  if (!card) {
    return null;
  }
  return isJokerCard(card) && Number.isInteger(card.effective_rank)
    ? card.effective_rank
    : card.rank;
}

function playerForSeat(snapshot, seat) {
  return snapshot?.players?.find((player) => player.seat === seat) || null;
}

export function currentGameState(snapshot) {
  return snapshot?.game_state || null;
}

export function isMyTurn(snapshot, seat) {
  return snapshot?.current_turn_seat === seat;
}

export function getPrivateCards(privateState) {
  return privateState?.private_cards || [];
}

export function canChoosePublicCards({ snapshot, privateState, seat }) {
  const self = playerForSeat(snapshot, seat);
  return (
    currentGameState(snapshot) === "PLAYERS_CHOOSE_PUBLIC_CARDS" &&
    self &&
    self.public_cards.length === 0 &&
    getPrivateCards(privateState).length >= 3
  );
}

export function hasPendingHiddenTake({ privateState }) {
  return Boolean(privateState?.pending_hidden_take);
}

export function optionalTakeRuleEnabled({ snapshot }) {
  return Boolean(snapshot?.rules?.allow_optional_take_pile);
}

export function getPendingJokerCard({ privateState }) {
  return privateState?.pending_joker_card || null;
}

export function hasPendingJokerSelection({ privateState }) {
  return Boolean(
    privateState?.pending_joker_selection && getPendingJokerCard({ privateState }),
  );
}

export function getSelectedNonJokerRank(cards = []) {
  const ranks = [
    ...new Set(
      cards.filter((card) => !isJokerCard(card)).map((card) => card.rank),
    ),
  ];
  if (ranks.length !== 1) {
    return null;
  }
  return ranks[0];
}

export function getSelectedHasJoker(cards = []) {
  return cards.some((card) => isJokerCard(card));
}

function getSelectedRank({ selectedCards = [], jokerRank = null }) {
  if (selectedCards.length === 0) {
    return null;
  }
  const nonJokerRank = getSelectedNonJokerRank(selectedCards);
  if (nonJokerRank !== null) {
    return nonJokerRank;
  }
  return jokerRank;
}

export function getPlayRank({ selectedCards = [], jokerRank = null }) {
  return getSelectedHasJoker(selectedCards)
    ? jokerRank
    : getSelectedRank({ selectedCards, jokerRank });
}

export function hasHighLowChoice(choice) {
  return ["HIGHER", "LOWER"].includes(choice);
}

export function getJokerOptions({ snapshot, cards = [] }) {
  const filteredCards = cards.filter(Boolean);
  if (!filteredCards.some((card) => isJokerCard(card))) {
    return [];
  }

  const validRanks = new Set(snapshot?.current_valid_ranks || []);
  const nonJokerRanks = [
    ...new Set(
      filteredCards
        .filter((card) => !isJokerCard(card))
        .map((card) => card.rank),
    ),
  ];

  if (nonJokerRanks.length > 1) {
    return [];
  }

  if (nonJokerRanks.length === 1) {
    const [rank] = nonJokerRanks;
    return JOKER_ALLOWED_RANKS.includes(rank) && validRanks.has(rank)
      ? [rank]
      : [];
  }

  return JOKER_ALLOWED_RANKS.filter((rank) => validRanks.has(rank));
}

export function hasPlayablePrivateCard({ snapshot, privateState, seat }) {
  if (
    currentGameState(snapshot) !== "DURING_GAME" ||
    !isMyTurn(snapshot, seat)
  ) {
    return false;
  }

  const validRanks = new Set(snapshot?.current_valid_ranks || []);
  return getPrivateCards(privateState).some((card) => {
    if (isJokerCard(card)) {
      return JOKER_ALLOWED_RANKS.some((rank) => validRanks.has(rank));
    }
    return validRanks.has(card.rank);
  });
}

export function canPlayHiddenCard({ snapshot, privateState, seat }) {
  const self = playerForSeat(snapshot, seat);
  return (
    currentGameState(snapshot) === "DURING_GAME" &&
    isMyTurn(snapshot, seat) &&
    !hasPendingHiddenTake({ privateState }) &&
    self &&
    self.public_cards.length === 0 &&
    self.hidden_cards_count > 0 &&
    getPrivateCards(privateState).length === 0
  );
}

export function canOptionallyTakePile({ snapshot, privateState, seat }) {
  if (
    currentGameState(snapshot) !== "DURING_GAME" ||
    !isMyTurn(snapshot, seat)
  ) {
    return false;
  }
  if (
    !optionalTakeRuleEnabled({ snapshot }) ||
    (snapshot?.play_pile?.length || 0) === 0
  ) {
    return false;
  }
  return (
    !hasPendingJokerSelection({ privateState }) &&
    !hasPendingHiddenTake({ privateState })
  );
}

export function mustTakePile({ snapshot, privateState, seat }) {
  if (
    currentGameState(snapshot) !== "DURING_GAME" ||
    !isMyTurn(snapshot, seat)
  ) {
    return false;
  }
  if (hasPendingHiddenTake({ privateState })) {
    return true;
  }
  return (
    getPrivateCards(privateState).length > 0 &&
    !canPlayHiddenCard({ snapshot, privateState, seat }) &&
    !hasPlayablePrivateCard({ snapshot, privateState, seat })
  );
}

function turnTargetLabel(snapshot) {
  return (
    snapshot?.current_turn_display_name ||
    (Number.isInteger(snapshot?.current_turn_seat)
      ? `Seat ${snapshot.current_turn_seat}`
      : "the next player")
  );
}

function buildPrompt({
  snapshot,
  choosingPublicCards,
  isPlayDecisionPhase,
  pendingJokerSelection,
  pendingRevealedJoker,
  selectedHasJoker,
  jokerRank,
  currentPlayRank,
  pendingHiddenTake,
  hiddenCardPlayable,
  optionalTakeAvailable,
  requiredTakePile,
}) {
  if (!snapshot) {
    return "";
  }
  if (snapshot.status === "LOBBY") {
    return "Share the code, wait for enough players, then start.";
  }
  if (snapshot.status === "GAME_OVER") {
    return "Game over. The host can start a rematch.";
  }
  if (choosingPublicCards) {
    return "Pick 3 public cards for the table.";
  }
  if (isPlayDecisionPhase) {
    if (pendingJokerSelection) {
      if (pendingRevealedJoker) {
        return "Choose which rank the revealed joker should be.";
      }
      return "Choose how the revealed 7 changes the next player's turn.";
    }
    if (selectedHasJoker && !jokerRank) {
      return "Choose which rank the joker should be before playing.";
    }
    if (currentPlayRank === snapshot.rules.high_low_rank) {
      return "Choose how the 7 changes the next player's turn.";
    }
    if (pendingHiddenTake) {
      return "Your revealed hidden card cannot be played. Take the pile.";
    }
    if (hiddenCardPlayable) {
      if (optionalTakeAvailable) {
        return "Reveal a hidden card or take the pile.";
      }
      return "Your hidden cards are live. Reveal a hidden card.";
    }
    if (requiredTakePile) {
      return "No legal card to play. Take the pile.";
    }
    if (optionalTakeAvailable) {
      return "Tap matching cards from your hand or take the pile.";
    }
    return "Tap matching cards from your hand.";
  }
  if (currentGameState(snapshot) === "DURING_GAME") {
    return `Waiting for ${turnTargetLabel(snapshot)} to play.`;
  }
  return "Waiting for the game to begin.";
}

function buildTurnNotice(snapshot, { isMyTurn, prompt }) {
  let headline = "Waiting";
  if (!snapshot) {
    return {
      key: "none",
      headline,
      copy: prompt,
    };
  }

  if (snapshot.status === "GAME_OVER") {
    headline = `${
      snapshot.players?.find((player) => player.finished_position === 1)
        ?.display_name || "A player"
    } won`;
  } else if (snapshot.status === "LOBBY") {
    headline = "Lobby";
  } else if (isMyTurn) {
    headline =
      currentGameState(snapshot) === "PLAYERS_CHOOSE_PUBLIC_CARDS"
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
      snapshot.self_seat ?? "none",
    ].join(":"),
    headline,
    copy: prompt,
  };
}

export function deriveGameplayUiState({
  snapshot = null,
  privateState = null,
  seat = null,
  selectedCards = [],
  jokerRank = null,
  highLowChoice = "",
}) {
  const cards = getPrivateCards(privateState);
  const gameState = currentGameState(snapshot);
  const myTurn = isMyTurn(snapshot, seat);
  const choosingPublicCards = canChoosePublicCards({
    snapshot,
    privateState,
    seat,
  });
  const pendingCard = getPendingJokerCard({ privateState });
  const pendingJokerSelection = hasPendingJokerSelection({ privateState });
  const pendingRevealedJoker =
    pendingJokerSelection && isJokerCard(pendingCard);
  const currentPendingRank = pendingJokerSelection
    ? cardEffectiveRank(pendingCard)
    : null;
  const selectedHasJoker = getSelectedHasJoker(selectedCards);
  const selectedPlayRank = getPlayRank({ selectedCards, jokerRank });
  const currentPlayRank = pendingJokerSelection
    ? pendingRevealedJoker
      ? jokerRank
      : currentPendingRank
    : selectedPlayRank;
  const hasSelectedHighLowChoice = hasHighLowChoice(highLowChoice);
  const pendingHiddenTake = hasPendingHiddenTake({ privateState });
  const hiddenCardPlayable = canPlayHiddenCard({
    snapshot,
    privateState,
    seat,
  });
  const playablePrivateCard = hasPlayablePrivateCard({
    snapshot,
    privateState,
    seat,
  });
  const optionalTakeEnabled = optionalTakeRuleEnabled({ snapshot });
  const optionalTakeAvailable = canOptionallyTakePile({
    snapshot,
    privateState,
    seat,
  });
  const requiredTakePile = mustTakePile({ snapshot, privateState, seat });
  const isPlayDecisionPhase = gameState === "DURING_GAME" && myTurn;
  const showJokerChoiceUi =
    isPlayDecisionPhase && (pendingRevealedJoker || selectedHasJoker);
  const jokerChoices = pendingJokerSelection
    ? getJokerOptions({ snapshot, cards: [pendingCard] })
    : getJokerOptions({ snapshot, cards: selectedCards });
  const showHighLowChoiceUi =
    isPlayDecisionPhase &&
    !choosingPublicCards &&
    currentPlayRank === snapshot?.rules?.high_low_rank;
  const needsJokerRankChoice =
    showJokerChoiceUi && Number.isInteger(jokerRank) === false;
  const needsHighLowChoice = showHighLowChoiceUi && !hasSelectedHighLowChoice;
  const canPlaySelectedCards =
    selectedCards.length > 0 && !needsJokerRankChoice && !needsHighLowChoice;
  const showPlaySelectedAction =
    isPlayDecisionPhase &&
    !hiddenCardPlayable &&
    !requiredTakePile &&
    !pendingJokerSelection;
  const playSelectedDisabled =
    cards.length === 0 || needsJokerRankChoice || needsHighLowChoice;

  let primaryHandAction = null;
  if (choosingPublicCards) {
    primaryHandAction = {
      id: GAMEPLAY_PRIMARY_ACTIONS.CHOOSE_PUBLIC_CARDS,
      label: "Lock cards",
      disabled: false,
    };
  } else if (pendingJokerSelection) {
    primaryHandAction = {
      id: GAMEPLAY_PRIMARY_ACTIONS.RESOLVE_JOKER,
      label: pendingRevealedJoker ? "Play joker" : "Play revealed card",
      disabled: needsJokerRankChoice || needsHighLowChoice,
    };
  } else if (hiddenCardPlayable) {
    primaryHandAction = {
      id: GAMEPLAY_PRIMARY_ACTIONS.PLAY_HIDDEN_CARD,
      label: "Reveal hidden card",
      disabled: false,
    };
  } else if (showPlaySelectedAction) {
    primaryHandAction = {
      id: GAMEPLAY_PRIMARY_ACTIONS.PLAY_PRIVATE_CARDS,
      label: "Play cards",
      disabled: playSelectedDisabled,
    };
  }

  const waitingText =
    gameState === "DURING_GAME" && !myTurn
      ? `Waiting for ${turnTargetLabel(snapshot)}.`
      : "";
  const prompt = buildPrompt({
    snapshot,
    choosingPublicCards,
    isPlayDecisionPhase,
    pendingJokerSelection,
    pendingRevealedJoker,
    selectedHasJoker,
    jokerRank,
    currentPlayRank,
    pendingHiddenTake,
    hiddenCardPlayable,
    optionalTakeAvailable,
    requiredTakePile,
  });

  return {
    currentGameState: gameState,
    isMyTurn: myTurn,
    canChoosePublicCards: choosingPublicCards,
    canPlayHiddenCard: hiddenCardPlayable,
    hasPlayablePrivateCard: playablePrivateCard,
    hasPendingHiddenTake: pendingHiddenTake,
    optionalTakeRuleEnabled: optionalTakeEnabled,
    canOptionallyTakePile: optionalTakeAvailable,
    mustTakePile: requiredTakePile,
    privateCards: cards,
    turnTarget: turnTargetLabel(snapshot),
    turnGuidance: {
      prompt,
      waitingText,
      isWaitingTurn: Boolean(waitingText),
      isPlayDecisionPhase,
    },
    turnNotice: buildTurnNotice(
      snapshot
        ? {
            ...snapshot,
            self_seat: seat,
          }
        : snapshot,
      {
        isMyTurn: myTurn,
        prompt,
      },
    ),
    pendingJoker: {
      active: pendingJokerSelection,
      card: pendingCard,
      isRevealedJoker: pendingRevealedJoker,
      currentRank: currentPendingRank,
    },
    selectedPlay: {
      selectedCards,
      selectedHasJoker,
      currentPlayRank,
      jokerChoices,
      hasHighLowChoice: hasSelectedHighLowChoice,
      needsJokerRankChoice,
      needsHighLowChoice,
      canPlaySelectedCards,
    },
    actionPanel: {
      showTakePileAction: requiredTakePile || optionalTakeAvailable,
      takePileActionRequired: requiredTakePile,
      takePileActionOptional: optionalTakeAvailable,
      showHiddenAction: hiddenCardPlayable,
      showJokerChoiceUi,
      showHighLowChoiceUi,
      primaryHandAction,
      waitingText,
    },
  };
}
