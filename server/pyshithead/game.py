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
    TakeTowerRequest,
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
            self.__check_for_winners_and_losers()
            four_of_a_kind = self.play_pile.has_four_times_same_rank_from_top()
            if four_of_a_kind:
                self.rank_event = RankEvent(RankType.TOPRANK, 2)
                self.next_player_event = NextPlayerEvent.SAME
                self.burn_event = BurnEvent.YES
        if isinstance(req, HiddenCardRequest):
            if not self.get_player().eligible_play_hidden_card():
                raise ValueError("Not eligible to play hidden card")
            # TODO
            raise NotImplementedError("HiddenCardRequest Not Implemented")

        if isinstance(req, TakeTowerRequest):
            if self.get_player().private_cards.get_ranks() in self.valid_ranks:
                raise ValueError("Not allowed to take tower, Check private Cards")
            if self.get_player().eligible_play_hidden_card():
                raise ValueError("play hidden cards first")
            # TODO
            raise NotImplementedError("TakeTowerRequest Not Implemented")

        self.__update_valid_cards()
        self.__update_next_player()

    def get_player(self, player_id=None) -> Player:
        if player_id is None:
            return self.active_players.head.data
        else:
            return self.active_players[player_id]

    def __check_for_winners_and_losers(self):
        for player in self.active_players.traverse_single():
            if player.data.private_cards.is_empty():
                print(f"Player {player.data.id} is finished 🥂")
                self.ranking.append(player)
                self.active_players.remove_node(player)

            if len(self.active_players) == 1:
                self.ranking.append(player)
                print("Game is Over ⭐⭐⭐")
                exit()

    def __update_next_player(self):
        self.active_players.next(int(self.next_player_event))

    def __all_cards_valid(self) -> set[int]:
        return set(ALL_RANKS)

    def __update_valid_cards(self):
        self.valid_ranks = self.rank_event.get_valid_ranks(self.valid_ranks)
