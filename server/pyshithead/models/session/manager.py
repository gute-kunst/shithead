from __future__ import annotations

import secrets
import string
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from pyshithead.models.common import GameManager, request_models
from pyshithead.models.game import Card, HiddenCardRequest, MAX_PLAYERS, PrivateCardsRequest, PyshitheadError, SpecialRank
from pyshithead.models.session.models import (
    ActionErrorEvent,
    ActionRequest,
    CardModel,
    PlayerSnapshot,
    PrivateState,
    PrivateStateEvent,
    SessionAuthResponse,
    SessionSnapshot,
    SessionSnapshotEvent,
    SessionStatus,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_display_name(display_name: str) -> str:
    cleaned = " ".join(display_name.strip().split())
    if not cleaned:
        raise ValueError("Display name is required.")
    if len(cleaned) > 24:
        raise ValueError("Display name must be 24 characters or fewer.")
    return cleaned


@dataclass
class SessionPlayer:
    seat: int
    display_name: str
    token: str
    websocket: Optional[WebSocket] = None
    connected: bool = False
    last_seen: datetime = field(default_factory=_utc_now)

    def mark_connected(self, websocket: WebSocket):
        self.websocket = websocket
        self.connected = True
        self.last_seen = _utc_now()

    def mark_disconnected(self):
        self.websocket = None
        self.connected = False
        self.last_seen = _utc_now()


class GameSession:
    def __init__(self, invite_code: str, host_name: str):
        self.invite_code = invite_code
        self.status = SessionStatus.LOBBY
        self.game_manager: Optional[GameManager] = None
        self.players: list[SessionPlayer] = []
        self.last_status_message: str | None = None
        self.pending_joker_seat: int | None = None
        self.pending_joker_card: Card | None = None
        host = self._add_player(host_name)
        self.host_seat = host.seat
        self.host_token = host.token

    def _add_player(self, display_name: str) -> SessionPlayer:
        player = SessionPlayer(
            seat=len(self.players),
            display_name=_normalize_display_name(display_name),
            token=secrets.token_urlsafe(24),
        )
        self.players.append(player)
        return player

    def get_player_by_token(self, token: str) -> SessionPlayer:
        for player in self.players:
            if player.token == token:
                return player
        raise ValueError("Unknown player token.")

    def get_player_by_seat(self, seat: int) -> SessionPlayer:
        for player in self.players:
            if player.seat == seat:
                return player
        raise ValueError("Unknown player seat.")

    def join(self, display_name: str) -> SessionPlayer:
        if self.status != SessionStatus.LOBBY:
            raise ValueError("Game already started.")
        if len(self.players) >= MAX_PLAYERS:
            raise ValueError(f"Game is full. Maximum is {MAX_PLAYERS} players.")
        return self._add_player(display_name)

    def start(self, player_token: str):
        player = self.get_player_by_token(player_token)
        if player.seat != self.host_seat:
            raise ValueError("Only the host can start the game.")
        if self.status != SessionStatus.LOBBY:
            raise ValueError("Game already started.")
        if len(self.players) < 2:
            raise ValueError("At least 2 players are required to start.")

        self.game_manager = GameManager(player_ids=[player.seat for player in self.players])
        self.last_status_message = None
        self.pending_joker_seat = None
        self.pending_joker_card = None
        self._sync_status()

    def _serialize_card(self, card: Card) -> CardModel:
        return CardModel(
            rank=int(card.rank),
            suit=int(card.suit),
            effective_rank=card.effective_rank,
            is_joker=card.is_joker,
        )

    def _effective_rank(self, card: Card) -> int:
        return card.effective_rank if card.effective_rank is not None else int(card.rank)

    def _clear_pending_joker(self):
        self.pending_joker_seat = None
        self.pending_joker_card = None

    def _top_rank_chain_count(self, cards: list) -> int:
        if not cards:
            return 0
        top_rank = self._effective_rank(cards[0])
        rank_counter = 1
        for card in cards[1:]:
            card_rank = self._effective_rank(card)
            if card_rank == top_rank:
                rank_counter += 1
                continue
            if card_rank == SpecialRank.INVISIBLE:
                continue
            break
        return rank_counter

    def _build_status_message(
        self,
        player: SessionPlayer,
        action_type: str,
        played_rank: int | None,
        choice: str,
        previous_play_pile: list,
        current_play_pile: list,
        played_card_count: int,
    ) -> str | None:
        if action_type == "take_play_pile":
            return f"{player.display_name} took the play pile."

        if action_type not in {"play_private_cards", "resolve_joker"} or played_rank is None:
            return None

        if played_rank == SpecialRank.HIGHLOW:
            if choice == "HIGHER":
                return "7 or higher!"
            if choice == "LOWER":
                return "7 or lower!"

        if played_rank == SpecialRank.BURN:
            return "Burn! 10 cleared the pile."

        if played_rank == SpecialRank.SKIP:
            return "Skip!"

        previous_chain_count = self._top_rank_chain_count(previous_play_pile)
        if previous_chain_count > 0 and self._effective_rank(previous_play_pile[0]) == played_rank:
            if previous_chain_count + played_card_count >= 4 and len(current_play_pile) == 0:
                return "Burn! Four of a kind cleared the pile."

        return None

    def _find_game_player(self, seat: int):
        if self.game_manager is None:
            return (None, False)

        for game_player in self.game_manager.game.active_players:
            if game_player.id_ == seat:
                return (game_player, False)

        for game_player in self.game_manager.game.ranking:
            if game_player.id_ == seat:
                return (game_player, True)

        return (None, False)

    def _sync_status(self):
        if self.game_manager is None:
            self.status = SessionStatus.LOBBY
        elif self.game_manager.game.state == "GAME_OVER":
            self.status = SessionStatus.GAME_OVER
        else:
            self.status = SessionStatus.IN_GAME

    def build_snapshot(self) -> SessionSnapshot:
        self._sync_status()
        players: list[PlayerSnapshot] = []
        finished_positions: dict[int, int] = {}

        if self.game_manager is not None:
            ranking = [player.id_ for player in self.game_manager.game.ranking]
            for position, seat in enumerate(ranking, start=1):
                finished_positions[seat] = position

        for player in self.players:
            game_player, has_finished = self._find_game_player(player.seat)
            public_cards = []
            hidden_cards_count = 0
            private_cards_count = 0

            if game_player is not None:
                public_cards = [self._serialize_card(card) for card in game_player.public_cards.cards]
                hidden_cards_count = len(game_player.hidden_cards)
                private_cards_count = len(game_player.private_cards)

            players.append(
                PlayerSnapshot(
                    seat=player.seat,
                    display_name=player.display_name,
                    is_host=player.seat == self.host_seat,
                    is_connected=player.connected,
                    has_finished=has_finished,
                    finished_position=finished_positions.get(player.seat),
                    public_cards=public_cards,
                    hidden_cards_count=hidden_cards_count,
                    private_cards_count=private_cards_count,
                )
            )

        if self.game_manager is None:
            return SessionSnapshot(
                invite_code=self.invite_code,
                status=self.status,
                host_seat=self.host_seat,
                players=players,
            )

        return SessionSnapshot(
            invite_code=self.invite_code,
            status=self.status,
            host_seat=self.host_seat,
                game_state=str(self.game_manager.game.state),
                current_turn_seat=self.game_manager.game.get_player().id_,
                current_turn_display_name=self.get_player_by_seat(
                    self.game_manager.game.get_player().id_
                ).display_name,
                current_valid_ranks=sorted(int(rank) for rank in self.game_manager.game.valid_ranks),
                status_message=self.last_status_message,
                pending_joker_selection=self.pending_joker_card is not None,
                cards_in_deck=len(self.game_manager.game.deck),
                play_pile=[self._serialize_card(card) for card in self.game_manager.game.play_pile.cards],
                players=players,
        )

    def build_private_state(self, seat: int) -> PrivateState:
        game_player, _ = self._find_game_player(seat)
        if game_player is None:
            return PrivateState(seat=seat, private_cards=[])
        return PrivateState(
            seat=seat,
            pending_joker_selection=self.pending_joker_seat == seat and self.pending_joker_card is not None,
            pending_joker_card=(
                self._serialize_card(self.pending_joker_card)
                if self.pending_joker_seat == seat and self.pending_joker_card is not None
                else None
            ),
            private_cards=[self._serialize_card(card) for card in game_player.private_cards.cards],
        )

    def auth_response(self, player: SessionPlayer) -> SessionAuthResponse:
        return SessionAuthResponse(
            invite_code=self.invite_code,
            player_token=player.token,
            seat=player.seat,
            snapshot=self.build_snapshot(),
            private_state=self.build_private_state(player.seat),
        )

    def _request_from_action(self, player: SessionPlayer, action: ActionRequest):
        cards = [request_models.CardModel(**card.dict()) for card in action.cards]
        if action.type == "choose_public_cards":
            return request_models.ChoosePublicCardsRequest(player_id=player.seat, cards=cards)
        if action.type == "play_private_cards":
            return request_models.PrivateCardsRequest(
                player_id=player.seat,
                cards=cards,
                choice=action.choice,
                joker_rank=action.joker_rank,
            )
        if action.type == "play_hidden_card":
            return request_models.HiddenCardRequest(player_id=player.seat)
        if action.type == "resolve_joker":
            return request_models.ResolveJokerRequest(
                player_id=player.seat,
                joker_rank=action.joker_rank or 0,
                choice=action.choice,
            )
        if action.type == "take_play_pile":
            return request_models.TakePlayPileRequest(player_id=player.seat)
        raise ValueError("Unsupported action type.")

    def apply_action(self, player_token: str, action: ActionRequest):
        if self.game_manager is None:
            raise ValueError("Game has not started yet.")

        player = self.get_player_by_token(player_token)
        previous_play_pile = list(self.game_manager.game.play_pile.cards)
        played_rank = None
        played_card_count = 0

        if self.pending_joker_card is not None:
            if player.seat != self.pending_joker_seat:
                raise ValueError("Waiting for the active player to choose the joker rank.")
            if action.type != "resolve_joker":
                raise ValueError("Choose the revealed joker rank before taking another action.")

            request = PrivateCardsRequest(
                player=self.game_manager.game.get_player(player.seat),
                cards=[self.pending_joker_card],
                choice=action.choice,
                joker_rank=action.joker_rank,
            )
            self.game_manager.game.process_playrequest(request)
            played_rank = action.joker_rank
            played_card_count = 1
            self._clear_pending_joker()
        elif action.type == "play_hidden_card":
            hidden_request = HiddenCardRequest(self.game_manager.game.get_player(player.seat))
            self.game_manager.game.process_hidden_card(hidden_request)
            revealed_card = next(iter(hidden_request.cards.cards))
            if revealed_card.is_joker:
                self.pending_joker_seat = player.seat
                self.pending_joker_card = revealed_card
                self.last_status_message = f"{player.display_name} revealed a joker."
            else:
                self.last_status_message = None
            self._sync_status()
            return
        else:
            request = self._request_from_action(player, action)
            self.game_manager.process_request(request)
            played_rank = (
                action.joker_rank
                if action.joker_rank is not None
                else (action.cards[0].effective_rank or action.cards[0].rank if action.cards else None)
            )
            played_card_count = len(action.cards)

        current_play_pile = list(self.game_manager.game.play_pile.cards)
        self.last_status_message = self._build_status_message(
            player=player,
            action_type=action.type,
            played_rank=played_rank,
            choice=action.choice,
            previous_play_pile=previous_play_pile,
            current_play_pile=current_play_pile,
            played_card_count=played_card_count,
        )
        self._sync_status()

    async def connect(self, player_token: str, websocket: WebSocket):
        player = self.get_player_by_token(player_token)
        await websocket.accept()
        player.mark_connected(websocket)
        await self.send_full_state(player)
        await self.broadcast_snapshot(exclude_seat=player.seat)

    async def disconnect(self, player_token: str):
        player = self.get_player_by_token(player_token)
        player.mark_disconnected()
        await self.broadcast_snapshot()

    async def _safe_send(self, websocket: Optional[WebSocket], payload: dict) -> bool:
        if websocket is None:
            return False
        if websocket.application_state == WebSocketState.DISCONNECTED:
            return False
        try:
            await websocket.send_json(payload)
            return True
        except Exception:
            return False

    async def send_full_state(self, player: SessionPlayer):
        snapshot_event = SessionSnapshotEvent(data=self.build_snapshot()).dict()
        private_state_event = PrivateStateEvent(data=self.build_private_state(player.seat)).dict()
        if not await self._safe_send(player.websocket, snapshot_event):
            player.mark_disconnected()
            return
        if not await self._safe_send(player.websocket, private_state_event):
            player.mark_disconnected()

    async def broadcast_snapshot(self, exclude_seat: int | None = None):
        snapshot_event = SessionSnapshotEvent(data=self.build_snapshot()).dict()
        for player in self.players:
            if player.seat == exclude_seat:
                continue
            if player.websocket is not None:
                sent = await self._safe_send(player.websocket, snapshot_event)
                if not sent:
                    player.mark_disconnected()

    async def broadcast_full_state(self):
        for player in self.players:
            if player.websocket is not None:
                await self.send_full_state(player)

    async def send_error(self, player_token: str, message: str):
        player = self.get_player_by_token(player_token)
        if player.websocket is not None:
            sent = await self._safe_send(player.websocket, ActionErrorEvent(message=message).dict())
            if not sent:
                player.mark_disconnected()


class GameSessionManager:
    def __init__(self):
        self.sessions: dict[str, GameSession] = {}

    def _generate_invite_code(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = "".join(secrets.choice(alphabet) for _ in range(6))
            if code not in self.sessions:
                return code

    def create_session(self, display_name: str) -> GameSession:
        session = GameSession(invite_code=self._generate_invite_code(), host_name=display_name)
        self.sessions[session.invite_code] = session
        return session

    def get_session(self, invite_code: str) -> GameSession:
        session = self.sessions.get(invite_code.upper())
        if session is None:
            raise ValueError("Game not found.")
        return session
