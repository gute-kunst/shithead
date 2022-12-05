from dataclasses import dataclass
from enum import IntEnum

from pyshithead import ALL_RANKS, BIGGEST_RANK, SpecialRank


class BurnEvent(IntEnum):
    NO = 1
    YES = 2


class Choice(IntEnum):
    HIGHER = 3
    LOWER = 4


class RankType(IntEnum):
    """
    TOPRANK: standard; all cards "">="" are valid incl. 2,5,10
    KEEPCURRENT: invisible
    HIGHER=Choice.HIGHER: all cards ">=" are valid (excl. 2,5)
    LOWER=Choice.LOWER: all cards <= are valid (excl 10)
    """

    TOPRANK = 1
    KEEPCURRENT = 2
    HIGHER = Choice.HIGHER
    LOWER = Choice.LOWER


@dataclass
class RankEvent:
    rank_type: RankType
    top_rank: int

    def get_valid_ranks(self, current_valid_ranks: set[int] = set(ALL_RANKS)) -> set[int]:
        valid_ranks: set[int] = set()
        if self.rank_type == RankType.TOPRANK:
            valid_ranks.update(
                [int(SpecialRank.RESET), int(SpecialRank.INVISIBLE), int(SpecialRank.BURN)]
            )
            valid_ranks.update([i for i in range(self.top_rank, BIGGEST_RANK + 1)])
        elif self.rank_type == RankType.HIGHER:
            valid_ranks.update([i for i in range(int(SpecialRank.HIGHLOW), BIGGEST_RANK + 1)])
        elif self.rank_type == RankType.LOWER:
            valid_ranks.update([i for i in range(2, int(SpecialRank.HIGHLOW) + 1)])
        elif self.rank_type == RankType.KEEPCURRENT:
            valid_ranks.update(current_valid_ranks)
        return valid_ranks
