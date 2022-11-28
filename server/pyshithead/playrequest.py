from abc import ABC, abstractmethod
from typing import List, Optional

from pyshithead import (
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
    def __init__(self, player: Player, cards: List = list(), choice: Optional[Choice] = None):
        self.player = player
        self.cards = SetOfCards(cards)
        self.choice: Optional[Choice] = choice

    def is_consistent(self):
        if not self.cards.rank_is_equal():
            raise ValueError("Rank is not equal")

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


class PublicCardsRequest(CardsRequest):
    def __init__(self, cards: List, choice: Optional[Choice]):
        self.cards = SetOfCards(cards)
        self.choice: Optional[Choice] = choice

    def is_consistent(self):
        if not self.cards.rank_is_equal():
            raise ValueError("Rank is not equal")
        if (
            self.choice in [Choice.HIGHER, Choice.LOWER]
            and self.cards.get_rank_if_equal() == SpecialRank.HIGHLOW
        ):
            raise ValueError("HigherLower defined but no HIGHLOW card was played")
        return True


class HiddenCardRequest(PlayRequest):
    pass


class TakeTowerRequest(PlayRequest):
    pass
