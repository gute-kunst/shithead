from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from pyshithead.models.game import SpecialRank


class SessionStatus(StrEnum):
    LOBBY = "LOBBY"
    IN_GAME = "IN_GAME"
    GAME_OVER = "GAME_OVER"


class CardModel(BaseModel):
    rank: int
    suit: int


class PlayerSnapshot(BaseModel):
    seat: int
    display_name: str
    is_host: bool
    is_connected: bool
    has_finished: bool
    finished_position: int | None = None
    public_cards: list[CardModel] = Field(default_factory=list)
    hidden_cards_count: int = 0
    private_cards_count: int = 0


class RulesSnapshot(BaseModel):
    high_low_rank: int = int(SpecialRank.HIGHLOW)


class SessionSnapshot(BaseModel):
    invite_code: str
    status: SessionStatus
    host_seat: int
    game_state: str | None = None
    current_turn_seat: int | None = None
    current_turn_display_name: str | None = None
    current_valid_ranks: list[int] = Field(default_factory=list)
    status_message: str | None = None
    cards_in_deck: int = 0
    play_pile: list[CardModel] = Field(default_factory=list)
    players: list[PlayerSnapshot] = Field(default_factory=list)
    rules: RulesSnapshot = Field(default_factory=RulesSnapshot)


class PrivateState(BaseModel):
    seat: int
    private_cards: list[CardModel] = Field(default_factory=list)


class SessionSnapshotEvent(BaseModel):
    type: Literal["session_snapshot"] = "session_snapshot"
    data: SessionSnapshot


class PrivateStateEvent(BaseModel):
    type: Literal["private_state"] = "private_state"
    data: PrivateState


class ActionErrorEvent(BaseModel):
    type: Literal["action_error"] = "action_error"
    message: str


class CreateGameRequest(BaseModel):
    display_name: str


class JoinGameRequest(BaseModel):
    display_name: str


class StartGameRequest(BaseModel):
    player_token: str


class ActionRequest(BaseModel):
    type: Literal[
        "choose_public_cards",
        "play_private_cards",
        "play_hidden_card",
        "take_play_pile",
    ]
    cards: list[CardModel] = Field(default_factory=list)
    choice: str = ""


class SessionAuthResponse(BaseModel):
    invite_code: str
    player_token: str
    seat: int
    snapshot: SessionSnapshot
    private_state: PrivateState
