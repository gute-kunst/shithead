from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Suit(Enum):
    TILES = 1
    HEART = 2
    CLOVERS = 3
    PIKES = 4


class Choice(Enum):
    HIGHER = 3
    LOWER = 4


class SpecialRank(Enum):
    RESET = 2
    INVISIBLE = 5
    HIGHLOW = 7
    SKIP = 8
    BURN = 10


class BurnEvent(Enum):
    NO = 1
    YES = 2


class RankType(Enum):
    TOPRANK = 1  # standard; all cards "">="" are valid incl. 2,5,10
    KEEPCURRENT = 2  # invisible
    HIGHER = Choice.HIGHER  # all cards ">=" are valid (excl. 2,5)
    LOWER = Choice.LOWER  # all cards <= are valid (excl 10)


@dataclass
class RankEvent:
    type: RankType
    top_rank: Optional[int] = None


@dataclass(frozen=True)
class Card:
    rank: int
    suit: Suit

    def __hash__(self):
        return hash(str(self.rank) + str(self.suit))

    def __eq__(self, other):
        return self.rank == other.rank and self.suit == other.suit
