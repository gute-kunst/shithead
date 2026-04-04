from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from pyshithead.models.game import JOKER_RANK


class Suit(IntEnum):
    TILES = 1
    HEART = 2
    CLOVERS = 3
    PIKES = 4
    JOKER_RED = 5
    JOKER_BLACK = 6


STANDARD_SUITS = [Suit.TILES, Suit.HEART, Suit.CLOVERS, Suit.PIKES]
JOKER_SUITS = [Suit.JOKER_RED, Suit.JOKER_BLACK]


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
    effective_rank: int | None = None
    high_low_choice: str | None = field(default=None, compare=False)

    @property
    def is_joker(self) -> bool:
        return self.rank == JOKER_RANK

    @property
    def resolved_rank(self) -> int:
        if self.is_joker and self.effective_rank is not None:
            return self.effective_rank
        return self.rank

    def with_effective_rank(
        self, effective_rank: int, *, high_low_choice: str | None = None
    ) -> "Card":
        return Card(
            rank=self.rank,
            suit=self.suit,
            effective_rank=effective_rank,
            high_low_choice=high_low_choice,
        )

    def __hash__(self):
        return hash(str(self.rank) + str(self.suit))

    def __eq__(self, other: object):
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank == other.rank and self.suit == other.suit

    def __repr__(self):
        return str(
            f"<rank: {self.rank} suit: {self.suit}"
            + (f" effective_rank: {self.effective_rank}" if self.effective_rank is not None else "")
            + ">"
        )
