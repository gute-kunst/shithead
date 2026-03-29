# isort: skip_file

NBR_HIDDEN_CARDS = 3
BIGGEST_RANK: int = 14
JOKER_RANK: int = BIGGEST_RANK + 1
NBR_JOKERS = 2
NBR_TOTAL_CARDS = 52 + NBR_JOKERS
ALL_RANKS = [i for i in range(2, BIGGEST_RANK + 1)]
RANK_PRECEDENCE_ORDER = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 12, 14]
RANK_PRECEDENCE = {rank: index for index, rank in enumerate(RANK_PRECEDENCE_ORDER)}
JOKER_ALLOWED_RANKS = [3, 4, 6, 7, 8, 9, 11, 13, 12, 14]
MAX_PLAYERS = 5


def rank_precedence(rank: int) -> int:
    return RANK_PRECEDENCE.get(rank, rank)


def sort_ranks_by_precedence(ranks) -> list[int]:
    return sorted([int(rank) for rank in ranks], key=rank_precedence)


def ranks_at_or_above(rank: int, ranks=ALL_RANKS) -> set[int]:
    threshold = rank_precedence(int(rank))
    return {int(candidate) for candidate in ranks if rank_precedence(int(candidate)) >= threshold}


def ranks_at_or_below(rank: int, ranks=ALL_RANKS) -> set[int]:
    threshold = rank_precedence(int(rank))
    return {int(candidate) for candidate in ranks if rank_precedence(int(candidate)) <= threshold}

from .errors import *
from .card import *
from .pile_of_cards import *
from .set_of_cards import *
from .player import *
from .events_and_states import *
from .linked_list import *
from .dealer import *
from .playrequest import *

from .game import *

from .view import *
