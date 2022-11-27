from enum import Enum

from gameplay import SetOfCards


class NextPlayerEvent(Enum):
    SAME = 0
    NEXT = 1
    NEXT_2 = 2  # skip
    NEXT_3 = 3  # skip double
    NEXT_4 = 3  # skip tripple


class Player:
    def __init__(self, id: int):
        self.id: int = id
        self.public_cards = SetOfCards()
        self.hidden_cards = SetOfCards()
        self.private_cards = SetOfCards()

    def __repr__(self):
        return str(self.id)

    def __eq__(self, other):
        return self.id == other.id

    def eligible_play_hidden_card(self) -> bool:
        if not self.private_cards.is_empty():
            print("Private Cards are not empty")
            return False
        if not self.public_cards.is_empty():
            print("Public Cards are not empty")
            return False
        return True

    def fillup_cards_from_own(self):
        if not self.private_cards.is_empty():
            return
        else:
            if not self.public_cards.is_empty():
                self.private_cards.put(self.public_cards.take_all())
