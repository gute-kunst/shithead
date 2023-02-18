# isort: skip_file

NBR_HIDDEN_CARDS = 3
NBR_TOTAL_CARDS = 52
BIGGEST_RANK: int = int((NBR_TOTAL_CARDS / 4) + 1)
ALL_RANKS = [i for i in range(2, BIGGEST_RANK + 1)]
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
from .game_manager import *
