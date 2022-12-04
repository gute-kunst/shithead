from abc import ABC, abstractmethod
from typing import Optional

from pyshithead import (
    NBR_HIDDEN_CARDS,
    BurnEvent,
    Card,
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


class CardsRequest(PlayRequest, ABC):
    cards: SetOfCards
    choice: Optional[Choice]

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
        if self.get_rank() == SpecialRank.BURN:
            burn_event = BurnEvent.YES
        return burn_event

    def cards_on_players_hands(self):
        if not self.cards in self.player.private_cards:
            print("Cards not in players private hands")
            return False
        return True

    def ranks_are_equal(self):
        if not self.cards.rank_is_equal():
            print("Rank is not equal")
            return False
        return True

    def high_low_consistency(self):
        if self.cards.get_rank_if_equal() == SpecialRank.HIGHLOW and self.choice not in [
            Choice.HIGHER,
            Choice.LOWER,
        ]:
            print("HighLow card was played but no Choice was provided")
            return False

        if (
            self.choice in [Choice.HIGHER, Choice.LOWER]
            and self.cards.get_rank_if_equal() != SpecialRank.HIGHLOW
        ):
            print("HigherLower Choice but no HIGHLOW card was played")
            return False
        return True


class PrivateCardsRequest(CardsRequest):
    def __init__(
        self,
        player: Player,
        cards: list[Card],
        choice: Optional[Choice] = None,
        consistency_check: bool = True,
    ):
        self.player = player
        self.cards = SetOfCards(cards)
        self.choice: Optional[Choice] = choice
        if consistency_check:
            if not self.is_consistent():
                raise ValueError("Request not consistent")

    def is_consistent(self) -> bool:
        if (
            not self.cards_on_players_hands()
            or not self.ranks_are_equal()
            or not self.high_low_consistency()
        ):
            return False
        return True


class HiddenCardRequest(CardsRequest):
    def __init__(
        self,
        player: Player,
        consistency_check: bool = True,
    ):
        self.player = player
        if consistency_check:
            if not self.is_consistent():
                raise ValueError("Request not consistent")

        self.cards: Card = self.player.hidden_cards.return_single()

    def is_consistent(self):
        if not self.player.eligible_to_play_hidden_card():
            return False
        return True


class ChoosePublicCardsRequest(CardsRequest):
    """
    Request used in the begin of the game, each Player selects 3 cards to be publicly shown to all other players
    """

    def __init__(
        self,
        player: Player,
        public_choice_cards: list,
        consistency_check: bool = True,
    ):
        self.player: Player = player
        self.cards: SetOfCards = SetOfCards(public_choice_cards)
        if consistency_check:
            if not self.is_consistent():
                raise ValueError("Request not consistent")

    def correct_number_was_chosen(self):
        if len(self.cards) != NBR_HIDDEN_CARDS:
            print("3 cards need to be selected")
            return False
        return True

    def is_consistent(self):
        if (
            not self.cards_on_players_hands()
            or not self.correct_number_was_chosen()
            or not self.player.eligible_to_choose_cards()
        ):
            return False
        return True

    def process(self):
        self.player.public_cards.put(self.player.private_cards.take(self.cards.cards))
        self.player.public_cards_were_selected = True


class TakePlayPileRequest(PlayRequest):
    def __init__(self, player: Player, consistency_check: bool = True):
        self.player: Player = player
        if consistency_check:
            if not self.is_consistent():
                raise ValueError("Request not consistent")

    def is_consistent(self):
        return True
