from abc import ABC, abstractmethod
from typing import Optional

from pyshithead import (
    NBR_HIDDEN_CARDS,
    BurnEvent,
    Choice,
    NextPlayerEvent,
    Player,
    RankEvent,
    RankType,
    SetOfCards,
    SpecialRank,
)


class PlayRequest(ABC):
    player: Player

    @abstractmethod
    def is_consistent(self):
        raise NotImplementedError("virtual method")


class CardsRequest(PlayRequest):
    def __init__(self, player: Player, cards: list, choice: Optional[Choice] = None):
        self.player = player
        self.cards = SetOfCards(cards)
        self.choice: Optional[Choice] = choice

    @abstractmethod
    def is_consistent(self):
        raise NotImplementedError("virtual method")

    def get_rank(self):
        return self.cards.get_rank_if_equal()

    def get_rank_event(self) -> RankEvent:
        top_rank = self.cards.get_rank_if_equal()
        rank_type = RankType.TOPRANK
        if self.choice in [Choice.HIGHER, Choice.LOWER]:
            rank_type = RankType(self.choice)
        if top_rank == SpecialRank.INVISIBLE:
            rank_type = RankType.KEEPCURRENT
        if top_rank == SpecialRank.BURN:
            top_rank = 2
        return RankEvent(rank_type, int(top_rank))

    def get_next_player_event(self) -> NextPlayerEvent:
        next_player_event = NextPlayerEvent.NEXT
        ranks = self.cards.get_ranks()
        if ranks[0] == SpecialRank.SKIP:
            if len(ranks) == 1:
                next_player_event = NextPlayerEvent.NEXT_2
            elif len(ranks) == 2:
                next_player_event = NextPlayerEvent.NEXT_3
            elif len(ranks) == 3:
                next_player_event = NextPlayerEvent.NEXT_4
        if ranks[0] == SpecialRank.BURN:
            next_player_event = NextPlayerEvent.SAME
        return next_player_event

    def get_burn_event(self) -> BurnEvent:
        burn_event = BurnEvent.NO
        if self.cards.get_ranks() == SpecialRank.BURN:
            burn_event = BurnEvent.YES
        return burn_event


class PrivateCardsRequest(CardsRequest):
    def __init__(self, player: Player, cards: list, choice: Optional[Choice] = None):
        self.player = player
        self.cards = SetOfCards(cards)
        self.choice: Optional[Choice] = choice
        self.is_consistent()

    def is_consistent(self):
        if not self.cards in self.player.private_cards:
            raise ValueError("Cards not in players private hands")
        if not self.cards.rank_is_equal():
            raise ValueError("Rank is not equal")
        if (
            self.choice in [Choice.HIGHER, Choice.LOWER]
            and self.cards.get_rank_if_equal() == SpecialRank.HIGHLOW
        ):
            raise ValueError("HigherLower defined but no HIGHLOW card was played")
        return True


class ChoosePublicCardsRequest(CardsRequest):
    def __init__(self, player: Player, hidden_choice_cards: list):
        self.player: Player = player
        self.cards: SetOfCards = SetOfCards(hidden_choice_cards)
        self.is_consistent()

    def is_consistent(self):
        if not self.cards in self.player.private_cards:
            raise ValueError("Cards not in players private hands")
        if len(self.cards) != NBR_HIDDEN_CARDS:
            raise ValueError("3 cards need to be selected")
        if self.player.selected_hidden_cards:
            raise ValueError("hidden cards were selected already")

    def process(self):
        self.player.public_cards.put(self.player.private_cards.take(self.cards.cards))
        self.player.selected_hidden_cards = True


class HiddenCardRequest(CardsRequest):
    pass


class TakeTowerRequest(PlayRequest):
    pass
