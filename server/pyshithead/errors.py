from typing import Optional

from pyshithead import NBR_HIDDEN_CARDS


class PyshitheadError(Exception):
    def __init__(self, message: str, object_id: Optional[str] = None):
        self.message = message
        self.object_id = object_id
        super().__init__(self.message)


class CardsRequestRanksNotEqualError(PyshitheadError):
    def __init__(self):
        super().__init__(
            message="Ranks in PlayCardRequest should be equal",
        )


class CardsNotInPlayersPrivateHandsError(PyshitheadError):
    def __init__(self):
        super().__init__(
            message="Cards are not in players private hands",
        )


class CardsRequestHighLowCardWithoutChoiceError(PyshitheadError):
    def __init__(self):
        super().__init__(
            message="HighLow card was played but no Choice was provided",
        )


class CardsRequestHighLowChoiceWithoutHighLowCardError(PyshitheadError):
    def __init__(self):
        super().__init__(
            message="HigherLower Choice but no HIGHLOW card was played",
        )


class NotEligibleForHiddenCardPlayError(PyshitheadError):
    def __init__(self, message):
        super().__init__(message=message)


class WrongNumberOfChosencardsError(PyshitheadError):
    def __init__(self):
        super().__init__(
            message=f"{NBR_HIDDEN_CARDS} cards need to be chosen",
        )


class PublicCardsWereSelectedAlreadyError(PyshitheadError):
    def __init__(self):
        super().__init__(
            message="Public cards were selected already",
        )
