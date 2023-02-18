from dataclasses import dataclass
from enum import Enum, IntEnum, StrEnum
from typing import Optional

from pyshithead.models.game import BIGGEST_RANK, Player, SpecialRank


class GameState(StrEnum):
    PLAYERS_CHOOSE_PUBLIC_CARDS = "PLAYERS_CHOOSE_PUBLIC_CARDS"
    DURING_GAME = "DURING_GAME"
    GAME_OVER = "GAME_OVER"


class NextPlayerEvent(IntEnum):
    SAME = 0
    NEXT = 1
    NEXT_2 = 2  # skip
    NEXT_3 = 3  # skip double
    NEXT_4 = 4  # skip triple

    def process(self, active_players):
        active_players.next(int(self))


class BurnEvent(IntEnum):
    NO = 1
    YES = 2

    def process(self, play_pile):
        if self == self.YES:
            play_pile.take_all()  # removes the cards


class Choice(StrEnum):
    HIGHER = "HIGHER"
    LOWER = "LOWER"


@dataclass
class PlayerIsFinishedEvent:
    player: Optional[Player]

    def process(self, ranking, active_players):
        if self.player is not None:
            ranking.append(self.player)
            active_players.remove_node(self.player)
            self.player = None


class RankType(Enum):
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

    def get_valid_ranks(self, current_valid_ranks: set[int]) -> set[int]:
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

    def process(self, valid_ranks):
        valid_ranks = self.get_valid_ranks(valid_ranks)


@dataclass
class PlayEvents:
    rank: RankEvent
    burn: BurnEvent
    next_player: NextPlayerEvent
    player_is_finished: PlayerIsFinishedEvent

    def process(self, play_pile, active_players, valid_ranks, ranking):
        self.burn.process(play_pile)
        self.next_player.process(active_players)
        self.rank.process(valid_ranks)
        self.player_is_finished.process(ranking, active_players)
