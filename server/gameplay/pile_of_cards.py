import random

from gameplay import Card, Suit


class PileOfCards:
    def __init__(self, cards: list[Card] = []):
        self.cards = cards

    def shuffle(self):
        random.shuffle(self.cards)

    def take(self, nbr_of_cards=int) -> list:
        retval = self.cards[:nbr_of_cards]
        del self.cards[:nbr_of_cards]
        return retval

    def take_all(self) -> list:
        retval = self.cards[:]
        del self.cards[:]
        return retval

    def is_empty(self):
        return True if len(self.cards) == 0 else False

    def __len__(self):
        return len(self.cards)

    @classmethod
    def generate_deck(cls):
        deck = PileOfCards([Card(i, suit) for suit in Suit for i in range(2, 15)])
        # deck = PileOfCards([Card(i, suit) for suit in Suit for i in range(1, 3)])

        deck.shuffle()
        return deck
