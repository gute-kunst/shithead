from typing import List, Set, Union

from gameplay import Card


class SetOfCards:
    def __init__(self, cards: Union[Set, List] = set()):
        self.cards: Set[Card] = set(cards)

    # specialty: RequestPileSpecialty = RequestPileSpecialty()

    def rank_is_equal(self):
        return all(card.rank == list(self.cards)[0].rank for card in self.cards)

    def __contains__(self, other):
        return other.cards.issubset(self.cards)

    def __len__(self):
        return len(self.cards)

    def is_empty(self):
        return True if len(self.cards) == 0 else False

    def add(self, cards: Union[Set, List]):
        self.cards.update(cards)
