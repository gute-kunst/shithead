from enum import IntEnum

from pyshithead import (
    NotEligibleForHiddenCardPlayError,
    PublicCardsWereSelectedAlreadyError,
    SetOfCards,
)


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

    def validate_eligible_to_play_hidden_card(self) -> bool:
        if not self.private_cards.is_empty():
            raise NotEligibleForHiddenCardPlayError(
                "Private cards need to be empty before playing hidden cards"
            )
        if not self.public_cards.is_empty():
            raise NotEligibleForHiddenCardPlayError(
                "Public cards need to be empty before playing hidden cards"
            )
        return True

    def validate_eligible_to_choose_cards(self):
        if self.public_cards_were_selected:
            raise PublicCardsWereSelectedAlreadyError
