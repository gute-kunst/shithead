from pyshithead import (
    ALL_RANKS,
    BurnEvent,
    ChoosePublicCardsRequest,
    CircularDoublyLinkedList,
    Dealer,
    HiddenCardRequest,
    NextPlayerEvent,
    PileOfCards,
    Player,
    PlayRequest,
    PrivateCardsRequest,
    RankEvent,
    RankType,
    TakePlayPileRequest,
)
from pyshithead.errors import *


class Game:
    def __init__(
        self,
        players: list[Player],
        deck: PileOfCards,
        play_pile: PileOfCards = PileOfCards(),
        game_id: int = 1,
    ):
        if len(players) > 5:
            raise ValueError("too many players")
        self.active_players: CircularDoublyLinkedList = CircularDoublyLinkedList(players)
        self.ranking: list[Player] = []
        self.valid_ranks: set[int] = self.__all_cards_valid()
        self.rank_event: RankEvent
        self.next_player_event: NextPlayerEvent
        self.burn_event: BurnEvent
        self.game_id: int = game_id
        self.play_pile: PileOfCards = play_pile
        self.deck: PileOfCards = deck

    @classmethod
    def initialize(
        cls,
        players: list[Player],
    ):
        game = cls(players=players, deck=Dealer.provide_shuffled_deck())
        Dealer.deal_cards_to_players(game.deck, game.active_players)
        return game

    def process_playrequest(self, req: PlayRequest):
        if isinstance(req, ChoosePublicCardsRequest):
            req.process()
            return
        if not req.player == self.get_player():
            raise RequestNotFromCurrentPlayerError(self.get_player())
        if isinstance(req, PrivateCardsRequest):
            if not req.get_rank() in self.valid_ranks:
                raise CardsNotEligibleOnPlayPileError
            self.rank_event = req.get_rank_event()
            self.next_player_event = req.get_next_player_event()
            self.burn_event = req.get_burn_event()
            self.play_pile.put(self.get_player().private_cards.take(req.cards.cards))
            Dealer.fillup_cards(self.deck, self.get_player())
            self.check_for_player_is_finished()
            four_of_a_kind = self.play_pile.has_four_times_same_rank_from_top()
            if four_of_a_kind:
                self.rank_event = RankEvent(RankType.TOPRANK, 2)
                self.next_player_event = NextPlayerEvent.SAME
                self.burn_event = BurnEvent.YES
        if isinstance(req, HiddenCardRequest):
            if not req.get_rank() in self.valid_ranks:
                raise NotImplementedError("HiddenCardRequest Not Implemented")
            else:
                # TODO if HIGHLOW --> ask user
                raise NotImplementedError("HiddenCardRequest Not Implemented")

        if isinstance(req, TakePlayPileRequest):
            if not set(self.get_player().private_cards.get_ranks()).isdisjoint(self.valid_ranks):
                raise TakePlayPileNotAllowed(
                    "TakePlayPile request not allowed, check private cards",
                    self.get_player().id_,
                )
            if self.get_player().eligible_to_play_hidden_card():
                raise TakePlayPileNotAllowed(
                    "TakePlayPile request not allowed, play hidden card",
                    self.get_player().id_,
                )
            self.burn_event = BurnEvent.NO
            self.next_player_event = NextPlayerEvent.NEXT
            self.rank_event = RankEvent(RankType.TOPRANK, 2)
            self.get_player().private_cards.put(self.play_pile.take_all())
        self.__process_burn()
        self.__update_valid_cards()
        self.update_next_player()
        if self.game_over():
            print(f"Ranking: {self.ranking}")
            exit()

    def __process_burn(self):
        if self.burn_event == BurnEvent.YES:
            self.play_pile.take_all()

    def game_over(self):
        if len(self.active_players) == 1:
            self.ranking.append(self.get_player())
            print("Game is Over ⭐⭐⭐")
            return True
        return False

    def get_player(self, player_id=None) -> Player:
        if player_id is None:
            return self.active_players.head.data
        else:
            return self.active_players[player_id]

    def check_for_player_is_finished(self):
        current_player = self.get_player()
        if current_player.has_no_cards_anymore():
            print(f"Player {current_player.id_} is finished 🥂")
            self.ranking.append(current_player)
            self.active_players.remove_node(current_player)
            return True
        return False

    def update_next_player(self):
        self.active_players.next(int(self.next_player_event))

    def __all_cards_valid(self) -> set[int]:
        return set(ALL_RANKS)

    def __update_valid_cards(self):
        self.valid_ranks = self.rank_event.get_valid_ranks(self.valid_ranks)

    def __str__(self) -> str:
        return str("Play order: " + str(self.active_players))
