from enum import IntEnum

from pyshithead import SetOfCards


class NextPlayerEvent(IntEnum):
    SAME = 0
    NEXT = 1
    NEXT_2 = 2  # skip
    NEXT_3 = 3  # skip double
    NEXT_4 = 4  # skip tripple


class Player:
    def __init__(self, id_: int):
        self.id_: int = id_
        self.public_cards = SetOfCards()
        self.hidden_cards = SetOfCards()
        self.private_cards = SetOfCards()
        self.public_cards_were_selected: int = False

    def __repr__(self):
        return str(self.id_)

    def __eq__(self, other):
        return self.id_ == other.id_

    def eligible_to_play_hidden_card(self) -> bool:
        if not self.private_cards.is_empty():
            print("Private Cards are not empty")
            return False
        if not self.public_cards.is_empty():
            print("Public Cards are not empty")
            return False
        return True

    def eligible_to_choose_cards(self) -> bool:
        if self.public_cards_were_selected:
            print("public cards were selected already")
            return False
        return True
