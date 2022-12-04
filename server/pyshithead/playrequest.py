from abc import ABC, abstractmethod
from typing import Optional

from pyshithead import (
    NBR_HIDDEN_CARDS,
    BurnEvent,
    Card,
    CardsNotInPlayersPrivateHandsError,
    CardsRequestHighLowCardWithoutChoiceError,
    CardsRequestHighLowChoiceWithoutHighLowCardError,
    CardsRequestRanksNotEqualError,
    Choice,
    NextPlayerEvent,
    Player,
    RankEvent,
    RankType,
    SetOfCards,
    SpecialRank,
    WrongNumberOfChosencardsError,
)


class PlayRequest(ABC):
    player: Player

    @abstractmethod
    def validate(self):
        raise NotImplementedError("virtual method")


class CardsRequest(PlayRequest, ABC):
    cards: SetOfCards
    choice: Optional[Choice]

    @abstractmethod
    def validate(self):
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

    def validate_cards_on_players_hands(self):
        if not self.cards in self.player.private_cards:
            raise CardsNotInPlayersPrivateHandsError()

    def validate_ranks_are_equal(self):
        if not self.cards.rank_is_equal():
            raise CardsRequestRanksNotEqualError()

    def validate_high_low_consistency(self):
        if self.cards.get_rank_if_equal() == SpecialRank.HIGHLOW and self.choice not in [
            Choice.HIGHER,
            Choice.LOWER,
        ]:
            raise CardsRequestHighLowCardWithoutChoiceError()

        if (
            self.choice in [Choice.HIGHER, Choice.LOWER]
            and self.cards.get_rank_if_equal() != SpecialRank.HIGHLOW
        ):
            raise CardsRequestHighLowChoiceWithoutHighLowCardError()


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
            self.validate()

    def validate(self):
        self.validate_cards_on_players_hands()
        self.validate_ranks_are_equal()
        self.validate_high_low_consistency()


class HiddenCardRequest(CardsRequest):
    def __init__(
        self,
        player: Player,
        consistency_check: bool = True,
    ):
        self.player = player
        if consistency_check:
            self.validate()

        self.cards: Card = self.player.hidden_cards.return_single()

    def validate(self):
        self.player.validate_eligible_to_play_hidden_card()


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
            self.validate()

    def validate_correct_number_was_chosen(self):
        if len(self.cards) != NBR_HIDDEN_CARDS:
            raise WrongNumberOfChosencardsError()

    def validate(self):
        self.validate_cards_on_players_hands()
        self.validate_correct_number_was_chosen()
        self.player.validate_eligible_to_choose_cards()

    def process(self):
        self.player.public_cards.put(self.player.private_cards.take(self.cards.cards))
        self.player.public_cards_were_selected = True


class TakePlayPileRequest(PlayRequest):
    def __init__(self, player: Player, consistency_check: bool = True):
        self.player: Player = player
        if consistency_check:
            self.validate()

    def validate(self):
        pass
