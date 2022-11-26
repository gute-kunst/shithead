from gameplay import NBR_HIDDEN_CARDS, PileOfCards, Player


class Game:
    def __init__(self, players: list[Player]):
        if len(players) > 5:
            raise ValueError("too many players")
        self.players = players
        self.deck = PileOfCards.generate_deck()
        self.play_pile = PileOfCards()

    def deal_cards(self):
        for player in self.players:
            player.hidden_cards.add(self.deck.take(NBR_HIDDEN_CARDS))
            player.private_cards.add(self.deck.take(NBR_HIDDEN_CARDS * 2))
