import json
import sys

from pydantic import BaseModel
from pydantic.schema import schema

from pyshithead.models.game import Choice, Player, SpecialRank


class CardModel(BaseModel):
    rank: int
    suit: int


class PlayerPublicInfo(BaseModel):
    id: int
    public_cards: list[CardModel]
    nbr_hidden_cards: int
    nbr_private_cards: int

    @classmethod
    def from_player(cls, player: Player):
        return cls(
            id=player.id_,
            public_cards=[vars(card) for card in player.public_cards.cards],
            nbr_hidden_cards=len(player.hidden_cards),
            nbr_private_cards=len(player.private_cards),
        )


class PlayerPrivateInfo(BaseModel):
    id: int
    private_cards: list[CardModel]

    @classmethod
    def from_player(cls, player: Player):
        return cls(id=player.id_, private_cards=[vars(card) for card in player.private_cards.cards])


class BaseRequest(BaseModel):
    player_id: int
    type: str


class TakePlayPileRequest(BaseRequest):
    type: str = "take_play_pile"


class HiddenCardRequest(BaseRequest):
    type: str = "hidden_card"


class ChoosePublicCardsRequest(BaseRequest):
    type: str = "choose_public_cards"
    cards: list[CardModel]


class PrivateCardsRequest(BaseRequest):
    type: str = "private_cards"
    cards: list[CardModel]
    choice: str = ""  # either empty string Choice.LOWER, Choice.HIGHER


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


class BaseResponse(BaseModel):
    type: str


class PublicInfoData(BaseModel):
    type: str = "public_info"
    game_id: int
    play_pile: list[CardModel]
    game_state: str
    nbr_of_cards_in_deck: int
    currents_turn: int
    player_public_info: list[PlayerPublicInfo]


class ChoiceModel(BaseModel):
    higher: str = Choice.HIGHER
    lower: str = Choice.LOWER


class RulesData(BaseModel):
    high_low_rank: int = SpecialRank.HIGHLOW
    # choice: ChoiceModel = ChoiceModel()


class Rules(BaseResponse):
    type: str = "rules"
    data: RulesData = RulesData()


class PublicInfo(BaseResponse):
    type: str = "public_info"
    data: PublicInfoData


class PrivateInfo(BaseResponse):
    type: str = "private_info"
    data: PlayerPrivateInfo


class ClientModel(BaseModel):
    type: str = "client_id"
    client_id: int

    @classmethod
    def from_client(cls, client):
        return cls(client_id=client.id_)


class GameTableData(BaseModel):
    nbr_of_players: int
    clients: list[ClientModel]


class GameTable(BaseModel):
    type: str = "current_game_table"
    data: GameTableData


class Log(BaseModel):
    type: str = "log"
    message: str


if __name__ == "__main__":

    top_level_schema = schema(
        [
            TakePlayPileRequest,
            HiddenCardRequest,
            ChoosePublicCardsRequest,
            PrivateCardsRequest,
            PublicInfo,
            PrivateInfo,
            Rules,
            GameTable,
            Log,
        ],
        title="Requests",
    )
    if sys.argv[1] != "outputfile":
        raise ValueError("only <outputfile> as argument supported")
    else:
        outputfile = sys.argv[2]

    with open(outputfile, "w", encoding="utf-8") as f:
        json.dump(top_level_schema, f, indent=4)
