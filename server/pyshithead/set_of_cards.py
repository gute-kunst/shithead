from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Set, Union

from pyshithead import Card


class SetOfCards:
    def __init__(self, cards: Union[Set, List] = set()):
        self.cards: Set[Card] = set(cards)

    def rank_is_equal(self):
        return all(card.rank == list(self.cards)[0].rank for card in self.cards)

    def get_rank_if_equal(self) -> Optional[int]:
        if self.rank_is_equal():
            return [card.rank for card in self.cards][0]
        return None

    def get_ranks(self) -> list[int]:
        return [card.rank for card in self.cards]

    def take(self, cards: Set) -> Set:
        if not cards.issubset(self.cards):
            raise ValueError("not all cards can be taken")
        intersect = self.cards.intersection(cards)
        self.cards = self.cards.difference(cards)
        return intersect

    def take_all(self):
        retval = self.cards
        self.cards = set()
        return retval

    def is_empty(self):
        return True if len(self.cards) == 0 else False

    def put(self, cards: Union[Set, List]):
        self.cards.update(cards)

    def __contains__(self, other):
        return other.cards.issubset(self.cards)

    def __eq__(self, other):
        return other.cards == self.cards

    def __len__(self):
        return len(self.cards)

    def __iter__(self):
        return iter(self.cards)
