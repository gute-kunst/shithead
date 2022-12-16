from pyshithead.models.game import PublicCardsWereSelectedAlreadyError, SetOfCards


class Player:
    def __init__(self, id_: int):
        self.id_: int = id_
        self.hidden_cards = SetOfCards()
        self.private_cards = SetOfCards()
        self.public_cards_were_selected: int = False
        self._public_cards = SetOfCards()

    @property
    def public_cards(self):
        return self._public_cards

    @public_cards.setter
    def public_cards(self, cards: SetOfCards):
        self._public_cards = cards
        self.public_cards_were_selected = True

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

    def get_public_info(self):
        return dict(
            {
                "id": self.id_,
                "public_cards": [vars(card) for card in self.public_cards.cards],
                "nbr_hidden_cards": len(self.hidden_cards),
                "nbr_private_cards": len(self.private_cards),
            }
        )

    def get_private_info(self):
        return dict(
            {
                "id": self.id_,
                "private_cards": [vars(card) for card in self.private_cards.cards],
            }
        )
