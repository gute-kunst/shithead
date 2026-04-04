from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from pyshithead.models.game import SpecialRank


class SessionStatus(StrEnum):
    LOBBY = "LOBBY"
    IN_GAME = "IN_GAME"
    GAME_OVER = "GAME_OVER"


class DisconnectAction(StrEnum):
    AUTO_PLAY_TURN = "AUTO_PLAY_TURN"
    AUTO_REMOVE_SETUP = "AUTO_REMOVE_SETUP"


class CardModel(BaseModel):
    rank: int
    suit: int
    effective_rank: int | None = None
    is_joker: bool = False


class PlayerSnapshot(BaseModel):
    seat: int
    display_name: str
    is_host: bool
    is_connected: bool
    last_seen_at: str
    disconnect_deadline_at: str | None = None
    disconnect_action: DisconnectAction | None = None
    has_finished: bool
    finished_position: int | None = None
    public_cards: list[CardModel] = Field(default_factory=list)
    hidden_cards_count: int = 0
    private_cards_count: int = 0


class RulesSnapshot(BaseModel):
    high_low_rank: int = int(SpecialRank.HIGHLOW)
    allow_optional_take_pile: bool = False


class ShoutoutPreset(BaseModel):
    key: str
    label: str
    emoji: str
    color: str


class SessionSnapshot(BaseModel):
    invite_code: str
    status: SessionStatus
    host_seat: int
    game_state: str | None = None
    current_turn_seat: int | None = None
    current_turn_display_name: str | None = None
    current_valid_ranks: list[int] = Field(default_factory=list)
    status_message: str | None = None
    pending_joker_selection: bool = False
    cards_in_deck: int = 0
    play_pile: list[CardModel] = Field(default_factory=list)
    players: list[PlayerSnapshot] = Field(default_factory=list)
    shoutout_presets: list[ShoutoutPreset] = Field(default_factory=list)
    rules: RulesSnapshot = Field(default_factory=RulesSnapshot)


class PrivateState(BaseModel):
    seat: int
    pending_joker_selection: bool = False
    pending_joker_card: CardModel | None = None
    pending_hidden_take: bool = False
    private_cards: list[CardModel] = Field(default_factory=list)
    shoutout_next_available_at: datetime | None = None


class ShoutoutEventData(BaseModel):
    event_id: str
    seat: int
    display_name: str
    preset: ShoutoutPreset


class SessionSnapshotEvent(BaseModel):
    type: Literal["session_snapshot"] = "session_snapshot"
    data: SessionSnapshot


class ShoutoutEvent(BaseModel):
    type: Literal["shoutout"] = "shoutout"
    data: ShoutoutEventData


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


class UpdateSettingsRequest(BaseModel):
    player_token: str
    allow_optional_take_pile: bool


class RestoreSessionRequest(BaseModel):
    player_token: str


class KickPlayerRequest(BaseModel):
    player_token: str


class ActionRequest(BaseModel):
    type: Literal[
        "choose_public_cards",
        "play_private_cards",
        "play_hidden_card",
        "resolve_joker",
        "take_play_pile",
        "send_shoutout",
    ]
    cards: list[CardModel] = Field(default_factory=list)
    choice: str = ""
    joker_rank: int | None = None
    shoutout_key: str = ""


class SessionAuthResponse(BaseModel):
    invite_code: str
    player_token: str
    seat: int
    snapshot: SessionSnapshot
    private_state: PrivateState
