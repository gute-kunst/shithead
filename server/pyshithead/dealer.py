from pyshithead import ALL_RANKS, NBR_HIDDEN_CARDS, Card, PileOfCards, Suit


class Dealer:
    def __init__(self) -> None:
        pass

    @classmethod
    def deal_cards_to_players(cls, deck: PileOfCards, active_players):
        for player in active_players.traverse_single():
            player.data.hidden_cards.put(deck.take_from_top(NBR_HIDDEN_CARDS))
            player.data.private_cards.put(deck.take_from_top(NBR_HIDDEN_CARDS * 2))
        # self.play_pile.put(deck.take(1))  ## Make move?
        # self.__update_valid_cards()

    @classmethod
    def provide_shuffled_deck(cls):
        deck = PileOfCards([Card(i, suit) for suit in Suit for i in ALL_RANKS])
        # deck = PileOfCards([Card(i, suit) for suit in Suit for i in range(1, 3)])
        deck.shuffle()
        return deck
