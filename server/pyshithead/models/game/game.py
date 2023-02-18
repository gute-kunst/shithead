from __future__ import annotations

from pyshithead.models.game import (
    ALL_RANKS,
    MAX_PLAYERS,
    ChoosePublicCardsRequest,
    CircularDoublyLinkedList,
    Dealer,
    GameState,
    HiddenCardRequest,
    PileOfCards,
    Player,
    PlayEvents,
    PlayRequest,
    PrivateCardsRequest,
    Suit,
    TakePlayPileRequest,
)
from pyshithead.models.game.errors import *


class Game:
    def __init__(
        self,
        players: list[Player],
        deck: PileOfCards,
        play_pile: PileOfCards = PileOfCards(),
        game_id: int = 1,
        state: GameState = GameState.PLAYERS_CHOOSE_PUBLIC_CARDS,
    ):
        if len(players) > MAX_PLAYERS:
            raise TooManyPlayersErrors(len(players), MAX_PLAYERS)
        self.active_players: CircularDoublyLinkedList = CircularDoublyLinkedList(players)
        self.ranking: list[Player] = []
        self.valid_ranks: set[int] = self.__all_cards_valid()
        self.game_id: int = game_id
        self.play_pile: PileOfCards = play_pile
        self.deck: PileOfCards = deck
        self.state: GameState = state

    @classmethod
    def initialize(cls, players: list[Player], ranks=ALL_RANKS, suits=Suit) -> Game:
        game = cls(players=players, deck=Dealer.provide_shuffled_deck(ranks, suits))
        Dealer.deal_cards_to_players(game.deck, game.active_players)
        game.state = GameState.PLAYERS_CHOOSE_PUBLIC_CARDS
        return game

    def process_choose_cards(self, req: ChoosePublicCardsRequest):
        req.process()
        if self.all_players_chosen_public_card():
            self.state = GameState.DURING_GAME

    def process_hidden_card(self, req: HiddenCardRequest):
        req.validate_player_and_state(self.get_player(), self.state)
        req.process()

    def process_playrequest(self, req: PlayRequest):
        req.validate_player_and_state(self.get_player(), self.state)
        if isinstance(req, PrivateCardsRequest):
            req.validate_cards_eligible(self.valid_ranks)
            events: PlayEvents = req.process(self.play_pile, self.deck)

        if isinstance(req, TakePlayPileRequest):
            req.validate(valid_ranks=self.valid_ranks)
            events = req.process(self.play_pile)

        events.process(self.play_pile, self.active_players, self.valid_ranks, self.ranking)
        self.check_for_game_over()

    def all_players_chosen_public_card(self):
        player_chosen_public_card = len(
            ["chosen" for player in self.active_players if player.public_cards_were_selected]
        )
        return player_chosen_public_card == len(self.active_players)

    def check_for_game_over(self):
        if len(self.active_players) == 1:
            self.ranking.append(self.get_player())
            print("Game is Over ⭐⭐⭐")
            print(f"Ranking: {self.ranking}")
            self.state = GameState.GAME_OVER

    def get_player(self, player_id=None) -> Player:
        if player_id is None:
            return self.active_players.head.data
        else:
            return self.active_players[player_id]

    def __all_cards_valid(self) -> set[int]:
        return set(ALL_RANKS)

    def __str__(self) -> str:
        return str("Play order: " + str(self.active_players))
