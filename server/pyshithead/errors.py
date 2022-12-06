from typing import Optional

from pyshithead import NBR_HIDDEN_CARDS


class PyshitheadError(Exception):
    def __init__(self, message: str, object_id: Optional[str] = None):
        self.message = message
        self.object_id = object_id
        super().__init__(self.message)


class RequestNotFromCurrentPlayerError(PyshitheadError):
    def __init__(self, player_id):
        super().__init__(message="It's another players turn", object_id=player_id)


class CardsRequestRanksNotEqualError(PyshitheadError):
    def __init__(self):
        super().__init__(
            message="Ranks in PlayCardRequest should be equal",
        )


class CardsNotEligibleOnPlayPileError(PyshitheadError):
    def __init__(self):
        super().__init__(
            message="Chosen cards are not eligible to play on play pile with current rule set",
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
    def __init__(self):
        super().__init__(message="Play private and public cards first")


class WrongNumberOfChosenCardsError(PyshitheadError):
    def __init__(self):
        super().__init__(
            message=f"{NBR_HIDDEN_CARDS} cards need to be chosen",
        )


class PublicCardsWereSelectedAlreadyError(PyshitheadError):
    def __init__(self):
        super().__init__(
            message="Public cards were selected already",
        )


class LinkedListEmptyError(PyshitheadError):
    def __init__(self):
        super().__init__(
            message="Linked List is empty",
        )


class LinkedListNodeNotFoundError(PyshitheadError):
    def __init__(self, node_id):
        super().__init__(message=f"Node with ID {node_id} not found", object_id=node_id)


class TakePlayPileNotAllowed(PyshitheadError):
    def __init__(self, message, player_id):
        super().__init__(
            message=message,
            object_id=player_id,
        )


class RequestNotAllowedInGameState(PyshitheadError):
    def __init__(self, player_id, game_state):
        super().__init__(
            message=f"Request not allowed in game state {game_state}",
            object_id=player_id,
        )
