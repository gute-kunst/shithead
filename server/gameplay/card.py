from dataclasses import dataclass
from enum import Enum


class Suit(Enum):
    TILES = 1
    HEART = 2
    CLOVERS = 3
    PIKES = 4


class RequestPileSpecialty(Enum):
    HIGHER = 1
    LOWER = 2


@dataclass(frozen=True)
class Card:
    rank: int
    suit: Suit

    def __hash__(self):
        return hash(str(self.rank) + str(self.suit))

    def __eq__(self, other):
        return self.rank == other.rank and self.suit == other.suit
