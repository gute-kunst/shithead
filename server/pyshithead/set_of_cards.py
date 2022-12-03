from typing import Optional

from pyshithead import Card


class SetOfCards:
    def __init__(self, cards: set | list = set()):
        self.cards: set[Card] = set(cards)

    def rank_is_equal(self):
        return all(card.rank == list(self.cards)[0].rank for card in self.cards)

    def get_rank_if_equal(self) -> Optional[int]:
        if self.rank_is_equal():
            return [card.rank for card in self.cards][0]
        return None

    def get_ranks(self) -> list[int]:
        return [card.rank for card in self.cards]

    def take(self, cards: set) -> set[Card]:
        if not cards.issubset(self.cards):
            raise ValueError("not all cards can be taken")
        intersect = self.cards.intersection(cards)
        self.cards = self.cards.difference(cards)
        return intersect

    def take_all(self) -> set[Card]:
        retval = self.cards
        self.cards = set()
        return retval

    def is_empty(self):
        return True if len(self.cards) == 0 else False

    def put(self, cards: set | list):
        self.cards.update(cards)

    def __contains__(self, other):
        return other.cards.issubset(self.cards)

    def __eq__(self, other):
        return other.cards == self.cards

    def __len__(self):
        return len(self.cards)

    def __iter__(self):
        return iter(self.cards)

    def isdisjoint(self, other):
        return self.cards.isdisjoint(other.cards)
