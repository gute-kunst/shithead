from pydantic import BaseModel

from pyshithead.models.game import PublicCardsWereSelectedAlreadyError, SetOfCards


class Player(BaseModel):
    id_: int
    hidden_cards: SetOfCards = SetOfCards()
    private_cards: SetOfCards = SetOfCards()
    public_cards_were_selected: int = False
    public_cards: SetOfCards = SetOfCards()

    # @property
    # def public_cards(self):
    #     return self._public_cards

    # @public_cards.setter
    # def public_cards(self, cards: SetOfCards):
    #     self._public_cards = cards
    #     self.public_cards_were_selected = True

    def __repr__(self):
        return str(self.id_)

    def __eq__(self, other):
        return self.id_ == other.id_

    def eligible_to_play_hidden_card(self) -> bool:
        if self.private_cards.is_empty() and self.public_cards.is_empty():
            return True
        return False

    def has_no_cards_anymore(self) -> bool:
        if (
            self.private_cards.is_empty()
            and self.public_cards.is_empty()
            and self.hidden_cards.is_empty()
        ):
            return True
        return False

    def validate_eligible_to_choose_cards(self):
        if self.public_cards_were_selected:
            raise PublicCardsWereSelectedAlreadyError
