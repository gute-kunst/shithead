from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Suit(IntEnum):
    TILES = 1
    HEART = 2
    CLOVERS = 3
    PIKES = 4


class SpecialRank(IntEnum):
    RESET = 2
    INVISIBLE = 5
    HIGHLOW = 7
    SKIP = 8
    BURN = 10


@dataclass(frozen=True)
class Card:
    rank: int
    suit: Suit

    def __hash__(self):
        return hash(str(self.rank) + str(self.suit))

    def __eq__(self, other: object):
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank == other.rank and self.suit == other.suit

    def __repr__(self):
        return str(f"<rank: {self.rank} suit: {self.suit}>")
