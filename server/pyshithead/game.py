from typing import List, Set

from pyshithead import (
    NBR_HIDDEN_CARDS,
    CircularDoublyLinkedList,
    PileOfCards,
    Player,
    PlayHiddenCardRequest,
    PlayPublicCardRequest,
    PlayRequest,
    PlayTakeTowerRequest,
    RankEvent,
)


class Game:
    def __init__(self, players: list[Player], id: int = 1):
        if len(players) > 5:
            raise ValueError("too many players")
        self.active_players: CircularDoublyLinkedList = CircularDoublyLinkedList(
            players
        )
        self.deck = PileOfCards.generate_deck()
        self.play_pile = PileOfCards()
        self.valid_ranks: Set[int]
        self.rank_event: RankEvent
        self.id = id
        self.ranking: List[Player] = []
        self.__deal_cards()

    def chosen_public_cards(self, cards, player_id):
        if self.cards_in_private(cards, player_id):
            # TODO
            pass

    def process_playrequest(self, req: PlayRequest):
        if not req.game_id == self.id:
            raise ValueError("game_id doesn't match game")
        if not req.player_id == self.get_player():
            raise ValueError("player_id doesn't match current player")
        # --> get_player() == current player is valid :)
        if not req.is_consistent():
            raise ValueError("Request is inconstistant")
        if isinstance(req, PlayPublicCardRequest):
            if not req.cards in self.get_player().private_cards:
                raise ValueError("Cards not in players private hands")
            if not req.get_rank() in self.valid_ranks:
                raise ValueError("Card Rank is invalid")
            self.rank_event = req.get_rank_event()
            self.next_player_event = req.get_next_player_event()
            self.burn_event = req.get_burn_event()
            self.play_pile.put(self.get_player().private_cards.take(req.cards.cards))
            self.fillup_cards(self.get_player())
            self.check_for_winners_and_losers()
            self.play_pile.get_pile_events()
        if isinstance(req, PlayHiddenCardRequest):
            if not self.get_player().eligible_play_hidden_card():
                raise ValueError("Not eligible to play hidden card")
        if isinstance(req, PlayTakeTowerRequest):
            if self.get_player().private_cards.get_ranks() in self.valid_ranks:
                raise ValueError("Not allowed to take tower, Check private Cards")
            if self.get_player().eligible_play_hidden_card():
                raise ValueError("play hidden cards first")

    def fillup_cards(self, player: Player):
        while len(player.private_cards) <= 3:
            if len(self.deck) > 0:
                player.private_cards.put(self.deck.take(1))
            else:
                player.fillup_cards_from_own()

    def check_for_winners_and_losers(self):
        for player in self.active_players.traverse_single():
            if player.data.private_cards.is_empty():
                print(f"Player {player.data.id} is finished 🥂")
                self.ranking.append(player)
                self.active_players.remove_node(player)

            if len(self.active_players) == 1:
                self.ranking.append(player)
                print("Game is Over ⭐⭐⭐")
                exit()

    def get_player(self, player_id=None) -> Player:
        if player_id == None:
            return self.active_players.head.data
        else:
            return self.active_players[player_id]

    def __update_valid_cards(self):
        pass

    def __deal_cards(self):
        for player in self.active_players.traverse_single():
            player.data.hidden_cards.put(self.deck.take(NBR_HIDDEN_CARDS))
            player.data.private_cards.put(self.deck.take(NBR_HIDDEN_CARDS * 2))
        self.play_pile.put(self.deck.take(1))  ## Make move?
        self.__update_valid_cards()
