import json
import sys
from typing import Optional

from pydantic import BaseModel
from pydantic.schema import schema


class BaseRequest(BaseModel):
    player_id: int
    type: str


class TakePlayPileRequest(BaseRequest):
    type = "take_play_pile"


class HiddenCardRequest(BaseRequest):
    type = "hidden_card"


class Card(BaseModel):
    rank: int
    suit: int


class ChoosePublicCardsRequest(BaseRequest):
    type = "choose_public_cards"
    cards: list[Card]


class PrivateCardsRequest(BaseRequest):
    type = "private_cards"
    cards: list[Card]
    choice: str  # either empty string Choice.LOWER, Choice.HIGHER


def request_factory(data) -> BaseRequest:
    if data["type"] == "private_cards":
        return PrivateCardsRequest(**data)
    elif data["type"] == "choose_public_cards":
        return ChoosePublicCardsRequest(**data)
    elif data["type"] == "hidden_card":
        return HiddenCardRequest(**data)
    elif data["type"] == "take_play_pile":
        return TakePlayPileRequest(**data)
    else:
        raise ValueError("wrong request type")  # TODO create custom error


if __name__ == "__main__":

    top_level_schema = schema(
        [TakePlayPileRequest, HiddenCardRequest, ChoosePublicCardsRequest, PrivateCardsRequest],
        title="Requests",
    )
    if sys.argv[1] != "outputfile":
        raise ValueError("only <outputfile> as argument supported")
    else:
        outputfile = sys.argv[2]

    with open(outputfile, "w", encoding="utf-8") as f:
        json.dump(top_level_schema, f, indent=4)
