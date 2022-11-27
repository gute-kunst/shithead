import random
from typing import List, Set, Union

from pyshithead import Card, Suit


class PileOfCards:
    def __init__(self, cards: List[Card] = []):
        self.cards: List[Card] = []
        for card in cards:
            self.cards.append(card)

    def shuffle(self):
        random.shuffle(self.cards)

    def take(self, nbr_of_cards=int) -> list:
        "returns card from the top ('[0]') of the tower"
        retval = self.cards[:nbr_of_cards]
        del self.cards[:nbr_of_cards]
        return retval

    def take_all(self) -> list:
        retval = self.cards[:]
        del self.cards[:]
        return retval

    def is_empty(self):
        return True if len(self.cards) == 0 else False

    def put(self, cards: Union[Set, List]):
        self.cards[0:0] = cards

    def get_pile_events(self):
        # TODO
        raise NotImplementedError()
        # rank_counter = 1
        # for i, card in enumerate(self.cards):
        #     print("⭐")
        #     if card.rank == self.cards[i + 1].rank or
        #     card.
        #     print(card)
        #     print(self.cards[i + 1])

    def __len__(self):
        return len(self.cards)

    def __getitem__(self, index):
        return self.cards[index]

    @classmethod
    def generate_deck(cls):
        deck = PileOfCards([Card(i, suit) for suit in Suit for i in range(2, 15)])
        # deck = PileOfCards([Card(i, suit) for suit in Suit for i in range(1, 3)])

        deck.shuffle()
        return deck
