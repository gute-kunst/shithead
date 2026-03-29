# isort: skip_file

NBR_HIDDEN_CARDS = 3
BIGGEST_RANK: int = 14
JOKER_RANK: int = BIGGEST_RANK + 1
NBR_JOKERS = 2
NBR_TOTAL_CARDS = 52 + NBR_JOKERS
ALL_RANKS = [i for i in range(2, BIGGEST_RANK + 1)]
JOKER_ALLOWED_RANKS = [3, 4, 6, 7, 8, 9, 11, 12, 13, 14]
MAX_PLAYERS = 5
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
