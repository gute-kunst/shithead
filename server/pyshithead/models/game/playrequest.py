from abc import ABC, abstractmethod
from typing import Optional

from pyshithead.models.game import (
    NBR_HIDDEN_CARDS,
    BurnEvent,
    Card,
    Choice,
    Dealer,
    GameState,
    NextPlayerEvent,
    PileOfCards,
    Player,
    PlayerIsFinishedEvent,
    PlayEvents,
    RankEvent,
    RankType,
    SetOfCards,
    SpecialRank,
)
from pyshithead.models.game.errors import *


class PlayRequest(ABC):
    player: Player

    @abstractmethod
    def validate(self):
        raise NotImplementedError("virtual method")

    def validate_player_and_state(self, player: Player, state: GameState):
        if not self.player == player:
            raise RequestNotFromCurrentPlayerError(self.player)
        if not state == GameState.DURING_GAME:
            raise RequestNotAllowedInGameStateError(self.player, state)


class TakePlayPileRequest(PlayRequest):
    def __init__(self, player: Player):
        self.player: Player = player

    def validate(self, valid_ranks):
        if not set(self.player.private_cards.get_ranks()).isdisjoint(valid_ranks):
            raise TakePlayPileNotAllowedError(
                "TakePlayPile request not allowed, check private cards",
                self.player.id_,
            )
        if self.player.eligible_to_play_hidden_card():
            raise TakePlayPileNotAllowedError(
                "TakePlayPile request not allowed, play hidden card",
                self.player.id_,
            )

    def get_play_events(self) -> PlayEvents:
        return PlayEvents(
            burn=BurnEvent.NO,
            next_player=NextPlayerEvent.NEXT,
            rank=RankEvent(RankType.TOPRANK, 2),
            player_is_finished=PlayerIsFinishedEvent(None),
        )

    def process(self, play_pile):
        self.player.private_cards.put(play_pile.take_all())
        return self.get_play_events()


class HiddenCardRequest(PlayRequest):
    def __init__(
        self,
        player: Player,
        consistency_check: bool = True,
    ):
        self.player = player
        if consistency_check:
            self.validate()

        self.cards: SetOfCards = SetOfCards([self.player.hidden_cards.return_single()])

    def validate(self):
        if not self.player.eligible_to_play_hidden_card():
            raise NotEligibleForHiddenCardPlayError

    def process(self):
        self.player.private_cards.put(self.player.hidden_cards.take(self.cards.cards))


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

    def get_play_events(self) -> PlayEvents:
        return PlayEvents(
            rank=self.get_rank_event(),
            burn=self.get_burn_event(),
            next_player=self.get_next_player_event(),
            player_is_finished=PlayerIsFinishedEvent(None),
        )

    def validate_cards_on_players_hands(self):
        if not self.cards in self.player.private_cards:
            raise CardsNotInPlayersPrivateHandsError

    def validate_ranks_are_equal(self):
        if not self.cards.rank_is_equal():
            raise CardsRequestRanksNotEqualError

    def validate_high_low_consistency(self):
        if self.cards.get_rank_if_equal() == SpecialRank.HIGHLOW and self.choice not in [
            Choice.HIGHER,
            Choice.LOWER,
        ]:
            raise CardsRequestHighLowCardWithoutChoiceError

        if (
            self.choice in [Choice.HIGHER, Choice.LOWER]
            and self.cards.get_rank_if_equal() != SpecialRank.HIGHLOW
        ):
            raise CardsRequestHighLowChoiceWithoutHighLowCardError

    def validate_cards_eligible(self, valid_ranks):
        if not self.get_rank() in valid_ranks:
            raise CardsNotEligibleOnPlayPileError


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

    @classmethod
    def from_dict(cls, player: Player, data: dict):
        return PrivateCardsRequest(
            player=player, cards=[Card(**card) for card in data["cards"]], choice=data["choice"]
        )

    def validate(self):
        self.validate_cards_on_players_hands()
        self.validate_ranks_are_equal()
        self.validate_high_low_consistency()

    def process(self, play_pile: PileOfCards, deck: PileOfCards):
        events = self.get_play_events()
        play_pile.put(self.player.private_cards.take(self.cards.cards))
        if self.player.has_no_cards_anymore():
            events.player_is_finished = PlayerIsFinishedEvent(self.player)
        Dealer.fillup_cards(deck, self.player)
        four_of_a_kind = play_pile.has_four_times_same_rank_from_top()
        if four_of_a_kind:
            events.rank = RankEvent(RankType.TOPRANK, 2)
            events.next_player = NextPlayerEvent.SAME
            events.burn = BurnEvent.YES
        return events


class ChoosePublicCardsRequest(CardsRequest):
    """
    Request used in the begin of the game, each Player selects 3 cards to be publicly shown to all other players
    """

    def __init__(
        self,
        player: Player,
        public_choice_cards: list[Card],
        consistency_check: bool = True,
    ):
        self.player: Player = player
        self.cards: SetOfCards = SetOfCards(public_choice_cards)
        if consistency_check:
            self.validate()

    @classmethod
    def from_dict(cls, player: Player, data: dict):
        return ChoosePublicCardsRequest(
            player=player,
            public_choice_cards=[Card(**card) for card in data["cards"]],
        )

    def validate_correct_number_was_chosen(self):
        if len(self.cards) != NBR_HIDDEN_CARDS:
            raise WrongNumberOfChosenCardsError

    def validate(self):
        self.player.validate_eligible_to_choose_cards()
        self.validate_correct_number_was_chosen()
        self.validate_cards_on_players_hands()

    def process(self):
        self.player.public_cards = SetOfCards(self.player.private_cards.take(self.cards.cards))
