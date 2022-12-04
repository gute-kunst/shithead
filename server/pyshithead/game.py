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


class Game:
    def __init__(self, players: list[Player], game_id: int = 1):
        if len(players) > 5:
            raise ValueError("too many players")
        self.active_players: CircularDoublyLinkedList = CircularDoublyLinkedList(players)
        self.ranking: list[Player] = []
        self.valid_ranks: set[int] = self.__all_cards_valid()
        self.rank_event: RankEvent
        self.next_player_event: NextPlayerEvent
        self.burn_event: BurnEvent
        self.game_id: int = game_id
        self.play_pile: PileOfCards = PileOfCards()
        self.deck: PileOfCards = Dealer.provide_shuffled_deck()
        Dealer.deal_cards_to_players(self.deck, self.active_players)

    def process_playrequest(self, req: PlayRequest):
        if isinstance(req, ChoosePublicCardsRequest):
            req.process()
            return
        if not req.player == self.get_player():
            raise ValueError("player_id doesn't match current player")
        if isinstance(req, PrivateCardsRequest):
            if not req.get_rank() in self.valid_ranks:
                raise ValueError("Card Rank is invalid")
            self.rank_event = req.get_rank_event()
            self.next_player_event = req.get_next_player_event()
            self.burn_event = req.get_burn_event()
            self.play_pile.put(self.get_player().private_cards.take(req.cards.cards))
            Dealer.fillup_cards(self.deck, self.get_player())
            if self.current_player_is_finished():
                raise NotImplementedError("player finish is not implemented")
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
                raise ValueError("Not allowed to take tower, Check private Cards")
            if self.get_player().eligible_to_play_hidden_card():
                raise ValueError("Play hidden card")

            self.burn_event = BurnEvent.NO
            self.next_player_event = NextPlayerEvent.NEXT
            self.rank_event = RankEvent(RankType.TOPRANK, 2)
            self.get_player().private_cards.put(self.play_pile.take_all())
        self.__process_burn()
        self.__update_valid_cards()
        self.__update_next_player()
        if self.__check_for_game_over():
            print(f"Ranking: {self.ranking}")
            exit()

    def __process_burn(self):
        if self.burn_event == BurnEvent.YES:
            self.play_pile.take_all()

    def __check_for_game_over(self):
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

    def current_player_is_finished(self):
        current_player = self.get_player()
        if current_player.private_cards.is_empty():
            print(f"Player {current_player.data.id_} is finished 🥂")
            self.ranking.append(current_player)
            self.active_players.remove_node(current_player)
            return True
        return False

    def __update_next_player(self):
        self.active_players.next(int(self.next_player_event))

    def __all_cards_valid(self) -> set[int]:
        return set(ALL_RANKS)

    def __update_valid_cards(self):
        self.valid_ranks = self.rank_event.get_valid_ranks(self.valid_ranks)

    def __str__(self) -> str:
        return str("Play order: " + str(self.active_players))
