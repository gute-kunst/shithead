from pyshithead import ALL_RANKS, NBR_HIDDEN_CARDS, Card, PileOfCards, Player, Suit


class Dealer:
    def __init__(self) -> None:
        pass

    @classmethod
    def deal_cards_to_players(cls, deck: PileOfCards, active_players):
        for player in active_players.traverse_single():
            player.data.hidden_cards.put(deck.take_from_top(NBR_HIDDEN_CARDS))
            player.data.private_cards.put(deck.take_from_top(NBR_HIDDEN_CARDS * 2))

    @classmethod
    def provide_shuffled_deck(cls):
        deck = PileOfCards([Card(i, suit) for suit in Suit for i in ALL_RANKS])
        # deck = PileOfCards([Card(i, suit) for suit in Suit for i in range(1, 3)])
        deck.shuffle()
        return deck

    @classmethod
    def fillup_cards(cls, deck: PileOfCards, player: Player):
        while len(player.private_cards) < NBR_HIDDEN_CARDS:
            if len(deck) > 0:
                player.private_cards.put(deck.take_from_top(1))
            else:
                if not player.private_cards.is_empty():
                    return
                else:
                    if not player.public_cards.is_empty():
                        player.private_cards.put(player.public_cards.take_all())
