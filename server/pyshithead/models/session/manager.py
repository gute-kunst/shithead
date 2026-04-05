from __future__ import annotations

import asyncio
import logging
import secrets
import string
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocketState

from pyshithead.models.common import GameManager, request_models
from pyshithead.models.game import (
    MAX_PLAYERS,
    Card,
    CircularDoublyLinkedList,
    Game,
    GameState,
    HiddenCardRequest,
    PileOfCards,
    Player,
    PrivateCardsRequest,
    PyshitheadError,
    RevealedCardsRequest,
    SetOfCards,
    SpecialRank,
    TakePlayPileRequest,
    rank_precedence,
    sort_ranks_by_precedence,
)
from pyshithead.models.session.models import (
    ActionErrorEvent,
    ActionRequest,
    CardModel,
    DisconnectAction,
    PlayerSnapshot,
    PrivateState,
    PrivateStateEvent,
    RulesSnapshot,
    SessionAuthResponse,
    SessionSnapshot,
    SessionSnapshotEvent,
    SessionStatus,
    ShoutoutEvent,
    ShoutoutEventData,
    ShoutoutPreset,
)
from pyshithead.models.session.store import SQLiteSessionStore

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_display_name(display_name: str) -> str:
    cleaned = " ".join(display_name.strip().split())
    if not cleaned:
        raise ValueError("Display name is required.")
    if len(cleaned) > 24:
        raise ValueError("Display name must be 24 characters or fewer.")
    return cleaned


SHOUTOUT_PRESET_DATA_BY_STATUS = {
    SessionStatus.LOBBY: (
        {
            "key": "lets-gooo",
            "label": "Let's gooo!",
            "emoji": "🎉",
            "color": "#B45309",  # festive amber — party energy
        },
        {
            "key": "shuffle-up-and-deal",
            "label": "Shuffle up and deal.",
            "emoji": "🃏",
            "color": "#1E3A5F",  # deep card table green-blue — casino
        },
        {
            "key": "optional-pile-takes",
            "label": "Shall we allow optional pile takes?",
            "emoji": "🤔",
            "color": "#6D4C41",  # warm brown — thoughtful
        },
        {
            "key": "obviously",
            "label": "Obviously!",
            "emoji": "💯",
            "color": "#15803D",  # strong green — confirmed yes
        },
        {
            "key": "nope",
            "label": "Nope.",
            "emoji": "👎",
            "color": "#991B1B",  # hard red — rejection
        },
        {
            "key": "may-the-worst-hand-lose",
            "label": "May the worst hand lose.",
            "emoji": "💩",
            "color": "#78350F",  # deep brown — obvious reasons 💩
        },
    ),
    SessionStatus.IN_GAME: (
        {
            "key": "hahaha",
            "label": "HAHAHA",
            "emoji": "😹",
            "color": "#FDE68A",
        },  # warm yellow — laughter
        {
            "key": "great-move",
            "label": "*!♧@#♢%^&",
            "emoji": "👿",
            "color": "#7C3AED",
        },  # deep purple — evil
        {
            "key": "wtf",
            "label": "Eat the pile, loser!",
            "emoji": "🗑️",
            "color": "#6B7280",
        },  # cool grey — trash
        {
            "key": "shit",
            "label": "That escalated quickly.",
            "emoji": "⚡",
            "color": "#1D4ED8",
        },  # electric blue — shock
        {
            "key": "nice",
            "label": "Burrrrn!",
            "emoji": "🔥",
            "color": "#EA580C",
        },  # deep orange — fire
        {
            "key": "oof",
            "label": "Well played \n ♦ ♣ ♠ ♥",
            "emoji": "🤝",
            "color": "#92400E",
        },  # warm brown — respect
        {
            "key": "how-just-how",
            "label": "How. Just HOW.",
            "emoji": "🤯",
            "color": "#DB2777",
        },  # hot pink — explosion
        {
            "key": "its-getting-hot-in-here",
            "label": "It's getting hot in here.",
            "emoji": "🌶️",
            "color": "#B91C1C",
        },  # chili red — spicy
        {
            "key": "good-vibes-only",
            "label": "Good vibes only!",
            "emoji": "🍀",
            "color": "#15803D",
        },  # rich green — luck
        {
            "key": "faster",
            "label": "FASTER!",
            "emoji": "⚡",
            "color": "#1E40AF",
        },  # deep blue — electric
    ),
    SessionStatus.GAME_OVER: (
        {
            "key": "expletive-burst",
            "label": "*!♧@#♢%^&",
            "emoji": "👿",
            "color": "#4C1D95",  # deep villain purple — rage demon
        },
        {
            "key": "rematch-immediately",
            "label": "Rematch. Immediately.",
            "emoji": "😈",
            "color": "#7F1D1D",  # dark blood red — vengeful energy
        },
        {
            "key": "that-doesnt-count",
            "label": "That doesn't count.",
            "emoji": "😤",
            "color": "#374151",  # stormy grey — dismissive
        },
        {
            "key": "that-was-intense",
            "label": "That was intense.",
            "emoji": "😮‍💨",
            "color": "#1E3A5F",  # deep exhale blue — relief/tension
        },
        {
            "key": "strong-game",
            "label": "Strong game!",
            "emoji": "💪",
            "color": "#1D4ED8",  # bold blue — strength/confidence
        },
        {
            "key": "sending-love",
            "label": "Sending Love",
            "emoji": "🫶",
            "color": "#9D174D",  # deep rose — warm love
        },
    ),
}


@dataclass
class SessionPlayer:
    seat: int
    display_name: str
    token: str
    websocket: Optional[WebSocket] = None
    connected: bool = False
    last_seen: datetime = field(default_factory=_utc_now)
    last_shoutout_at: datetime | None = None
    disconnect_deadline_at: datetime | None = None
    disconnect_action: DisconnectAction | None = None

    def mark_connected(self, websocket: WebSocket):
        self.websocket = websocket
        self.connected = True
        self.last_seen = _utc_now()
        self.disconnect_deadline_at = None
        self.disconnect_action = None

    def mark_disconnected(self):
        self.websocket = None
        self.connected = False
        self.last_seen = _utc_now()


@dataclass
class SessionSettings:
    sort_hand_cards: bool = True
    allow_optional_take_pile: bool = False


class SessionCache(dict):
    def __init__(self, clear_callback: Callable[[], None]):
        super().__init__()
        self._clear_callback = clear_callback

    def clear(self):
        self._clear_callback()
        super().clear()


class GameSession:
    ACTIVE_TURN_DISCONNECT_GRACE_SECONDS = 300
    SETUP_DISCONNECT_GRACE_SECONDS = 600
    LOBBY_REAP_AFTER = timedelta(hours=2)
    ACTIVE_REAP_AFTER = timedelta(minutes=30)
    SHOUTOUT_COOLDOWN_SECONDS = 4

    def __init__(
        self,
        invite_code: str,
        host_name: str,
        on_reap: Callable[[str], None] | None = None,
        on_change: Callable[["GameSession"], None] | None = None,
    ):
        self.invite_code = invite_code
        self.status = SessionStatus.LOBBY
        self.game_manager: Optional[GameManager] = None
        self.settings = SessionSettings()
        self.players: list[SessionPlayer] = []
        self.last_status_message: str | None = None
        self.pending_joker_seat: int | None = None
        self.pending_joker_card: Card | None = None
        self.pending_hidden_take_seat: int | None = None
        self.active_turn_disconnect_grace_seconds = self.ACTIVE_TURN_DISCONNECT_GRACE_SECONDS
        self.setup_disconnect_grace_seconds = self.SETUP_DISCONNECT_GRACE_SECONDS
        self.disconnect_timeout_tasks: dict[int, asyncio.Task] = {}
        self.last_activity_at = _utc_now()
        self._on_reap = on_reap
        self._on_change = on_change
        self._reap_task: asyncio.Task | None = None
        host = self._add_player(host_name)
        self.host_seat = host.seat
        self.host_token = host.token

    def _persist(self):
        if self._on_change is not None:
            self._on_change(self)

    def _touch(self):
        self.last_activity_at = _utc_now()

    def _has_connected_players(self) -> bool:
        return any(player.connected for player in self.players)

    def _reap_after(self) -> timedelta:
        return (
            self.LOBBY_REAP_AFTER if self.status == SessionStatus.LOBBY else self.ACTIVE_REAP_AFTER
        )

    def _reap_deadline(self) -> datetime:
        return self.last_activity_at + self._reap_after()

    def is_expired(self, now: datetime | None = None) -> bool:
        if self._has_connected_players():
            return False
        current_time = now or _utc_now()
        return current_time >= self._reap_deadline()

    def _add_player(self, display_name: str) -> SessionPlayer:
        player = SessionPlayer(
            seat=len(self.players),
            display_name=_normalize_display_name(display_name),
            token=secrets.token_urlsafe(24),
        )
        self.players.append(player)
        self._touch()
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
        player = self._add_player(display_name)
        self._sync_reap_schedule()
        self._persist()
        return player

    def start(self, player_token: str):
        player = self.get_player_by_token(player_token)
        if player.seat != self.host_seat:
            raise ValueError("Only the host can start the game.")
        if self.status != SessionStatus.LOBBY:
            raise ValueError("Game already started.")
        if len(self.players) < 2:
            raise ValueError("At least 2 players are required to start.")

        self._cancel_all_disconnect_timeouts()
        self.game_manager = GameManager(player_ids=[player.seat for player in self.players])
        self.last_status_message = None
        self.pending_joker_seat = None
        self.pending_joker_card = None
        self.pending_hidden_take_seat = None
        self._finalize_state_change()

    def update_settings(self, player_token: str, *, allow_optional_take_pile: bool):
        player = self.get_player_by_token(player_token)
        if player.seat != self.host_seat:
            raise ValueError("Only the host can change lobby settings.")
        if self.status != SessionStatus.LOBBY:
            raise ValueError("Lobby settings can only be changed before the game starts.")
        self.settings.allow_optional_take_pile = allow_optional_take_pile
        self._finalize_state_change()

    def rematch(self, player_token: str):
        player = self.get_player_by_token(player_token)
        if player.seat != self.host_seat:
            raise ValueError("Only the host can start a rematch.")
        self._sync_status()
        if self.status != SessionStatus.GAME_OVER:
            raise ValueError("Game is not over.")

        self._cancel_all_disconnect_timeouts()
        self.game_manager = None
        self.last_status_message = None
        self._clear_pending_joker()
        self._clear_pending_hidden_take()
        self._finalize_state_change()

    def _serialize_card(self, card: Card) -> CardModel:
        return CardModel(
            rank=int(card.rank),
            suit=int(card.suit),
            effective_rank=card.effective_rank,
            is_joker=card.is_joker,
            high_low_choice=card.high_low_choice,
        )

    def _sort_private_cards(self, cards) -> list[Card]:
        if not self.settings.sort_hand_cards:
            return list(cards)
        return sorted(
            cards,
            key=lambda card: (
                card.is_joker,
                rank_precedence(self._effective_rank(card)),
                int(card.suit),
            ),
        )

    def _rules_snapshot(self) -> RulesSnapshot:
        return RulesSnapshot(
            allow_optional_take_pile=self.settings.allow_optional_take_pile,
        )

    def _shoutout_preset_data(self, status: SessionStatus | None = None):
        return SHOUTOUT_PRESET_DATA_BY_STATUS.get(status or self.status, ())

    def _shoutout_presets(self, status: SessionStatus | None = None) -> list[ShoutoutPreset]:
        return [ShoutoutPreset(**preset) for preset in self._shoutout_preset_data(status)]

    def _get_shoutout_preset(
        self, shoutout_key: str, status: SessionStatus | None = None
    ) -> ShoutoutPreset:
        for preset in self._shoutout_preset_data(status):
            if preset["key"] == shoutout_key:
                return ShoutoutPreset(**preset)
        raise ValueError("Unknown shoutout preset.")

    def _effective_rank(self, card: Card) -> int:
        return card.effective_rank if card.effective_rank is not None else int(card.rank)

    def _clear_pending_joker(self):
        self.pending_joker_seat = None
        self.pending_joker_card = None

    def _clear_pending_hidden_take(self):
        self.pending_hidden_take_seat = None

    def _build_shoutout_event(self, player: SessionPlayer, shoutout_key: str) -> ShoutoutEvent:
        preset = self._get_shoutout_preset(shoutout_key)
        now = _utc_now()
        if player.last_shoutout_at is not None and now - player.last_shoutout_at < timedelta(
            seconds=self.SHOUTOUT_COOLDOWN_SECONDS
        ):
            raise ValueError("Please wait before sending another shoutout.")
        player.last_shoutout_at = now
        return ShoutoutEvent(
            data=ShoutoutEventData(
                event_id=secrets.token_urlsafe(8),
                seat=player.seat,
                display_name=player.display_name,
                preset=preset,
            )
        )

    def _get_player_entry(self, seat: int) -> SessionPlayer | None:
        return next((entry for entry in self.players if entry.seat == seat), None)

    def _clear_disconnect_tracking(self, player: SessionPlayer):
        player.disconnect_deadline_at = None
        player.disconnect_action = None

    def _cancel_all_disconnect_timeouts(self):
        for seat in list(self.disconnect_timeout_tasks):
            self._cancel_disconnect_timeout(seat)

    def _cancel_disconnect_timeout(self, seat: int):
        task = self.disconnect_timeout_tasks.pop(seat, None)
        if task is not None:
            task.cancel()

    def _cancel_reap_task(self):
        task = self._reap_task
        self._reap_task = None
        if task is None:
            return
        try:
            current_task = asyncio.current_task()
        except RuntimeError:
            current_task = None
        if task is not current_task:
            task.cancel()

    def _sync_reap_schedule(self):
        if self._has_connected_players() or self._on_reap is None:
            self._cancel_reap_task()
            return
        self._cancel_reap_task()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        delay = max(0, (self._reap_deadline() - _utc_now()).total_seconds())
        self._reap_task = loop.create_task(self._reap_runner(delay))

    async def _reap_runner(self, delay_seconds: float):
        try:
            await asyncio.sleep(delay_seconds)
            if self.is_expired() and self._on_reap is not None:
                self._on_reap(self.invite_code)
        except asyncio.CancelledError:
            return
        finally:
            current_task = asyncio.current_task()
            if self._reap_task is current_task:
                self._reap_task = None

    def shutdown(self):
        self._cancel_all_disconnect_timeouts()
        self._cancel_reap_task()
        self._clear_pending_joker()
        self._clear_pending_hidden_take()

    def _promote_host_if_needed(self):
        if any(player.seat == self.host_seat for player in self.players):
            return
        if not self.players:
            return
        replacement_host = self.players[0]
        self.host_seat = replacement_host.seat
        self.host_token = replacement_host.token

    def _infer_disconnect_action(self, seat: int) -> DisconnectAction | None:
        if self.game_manager is None:
            return None
        game = self.game_manager.game
        if game.state == GameState.PLAYERS_CHOOSE_PUBLIC_CARDS:
            return DisconnectAction.AUTO_REMOVE_SETUP
        if game.state == GameState.DURING_GAME and game.get_player().id_ == seat:
            return DisconnectAction.AUTO_PLAY_TURN
        return None

    def _sync_disconnect_policies(self):
        inferred_current_action = {
            player.seat: (
                self._infer_disconnect_action(player.seat) if not player.connected else None
            )
            for player in self.players
        }
        for player in self.players:
            desired_action = inferred_current_action[player.seat]
            if player.connected or desired_action is None:
                self._cancel_disconnect_timeout(player.seat)
                self._clear_disconnect_tracking(player)
                continue

            if player.disconnect_action != desired_action or player.disconnect_deadline_at is None:
                if desired_action == DisconnectAction.AUTO_REMOVE_SETUP:
                    player.disconnect_deadline_at = player.last_seen + timedelta(
                        seconds=self.setup_disconnect_grace_seconds
                    )
                else:
                    player.disconnect_deadline_at = _utc_now() + timedelta(
                        seconds=self.active_turn_disconnect_grace_seconds
                    )
                player.disconnect_action = desired_action

            self._schedule_disconnect_timeout(player)

    def _schedule_disconnect_timeout(self, player: SessionPlayer):
        self._cancel_disconnect_timeout(player.seat)
        if player.disconnect_deadline_at is None or player.disconnect_action is None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self.disconnect_timeout_tasks[player.seat] = loop.create_task(
            self._disconnect_timeout_runner(
                player.seat,
                player.disconnect_action,
                player.disconnect_deadline_at,
            )
        )

    def _finalize_state_change(self, *, touch: bool = True):
        if touch:
            self._touch()
        self._sync_status()
        self._sync_disconnect_policies()
        self._sync_reap_schedule()
        self._persist()

    def _handle_player_disconnect(self, player: SessionPlayer):
        player.mark_disconnected()
        self._finalize_state_change()

    async def _disconnect_timeout_runner(
        self,
        seat: int,
        action: DisconnectAction,
        deadline_at: datetime,
    ):
        try:
            delay = max(0, (deadline_at - _utc_now()).total_seconds())
            await asyncio.sleep(delay)
            await self._apply_disconnect_timeout(seat, action)
        except asyncio.CancelledError:
            return
        finally:
            current_task = asyncio.current_task()
            if self.disconnect_timeout_tasks.get(seat) is current_task:
                self.disconnect_timeout_tasks.pop(seat, None)

    def _remove_player_record(self, seat: int):
        self._cancel_disconnect_timeout(seat)
        player = self._get_player_entry(seat)
        if player is None:
            return
        self._clear_disconnect_tracking(player)
        self.players = [entry for entry in self.players if entry.seat != seat]
        self._promote_host_if_needed()

    def _remove_player_from_game(self, seat: int):
        if self.game_manager is None:
            return
        game = self.game_manager.game
        game_player, has_finished = self._find_game_player(seat)
        if self.pending_joker_seat == seat:
            self._clear_pending_joker()
        if self.pending_hidden_take_seat == seat:
            self._clear_pending_hidden_take()
        if has_finished:
            game.ranking = [player for player in game.ranking if player.id_ != seat]
            return
        if game_player is None:
            return
        if len(game.active_players) > 1:
            game.active_players.remove_node(game_player)
        if game.state != GameState.GAME_OVER and len(game.active_players) == 1:
            game.check_for_game_over()

    def _remove_setup_player(self, seat: int, *, status_message: str):
        player = self._get_player_entry(seat)
        if player is None or self.game_manager is None:
            return
        game = self.game_manager.game
        self._remove_player_from_game(seat)
        self._remove_player_record(seat)
        self.last_status_message = status_message
        if len(self.players) < 2 or len(game.active_players) < 2:
            self._cancel_all_disconnect_timeouts()
            self.game_manager = None
            self._clear_pending_joker()
            self._clear_pending_hidden_take()
            self.status = SessionStatus.LOBBY
            return
        if game.all_players_chosen_public_card():
            game.state = GameState.DURING_GAME

    def _resolve_current_offline_turn(
        self, seat: int, *, set_status_message: bool = True
    ) -> str | None:
        player = self._get_player_entry(seat)
        if player is None or self.game_manager is None:
            return None
        game = self.game_manager.game
        if game.state != GameState.DURING_GAME or game.get_player().id_ != seat:
            return None

        summary = "missed their turn"
        if self.pending_joker_seat == seat:
            timed_out_player = game.get_player(seat)
            take_request = TakePlayPileRequest(timed_out_player)
            game.process_playrequest(take_request, allow_when_hidden_available=True)
            revealed_name = self._card_status_name(self.pending_joker_card)
            self._clear_pending_joker()
            if set_status_message:
                self.last_status_message = f"{player.display_name} disconnected after revealing {revealed_name} and took the play pile."
            summary = f"took the play pile after revealing {revealed_name}"
        elif self.pending_hidden_take_seat == seat:
            timed_out_player = game.get_player(seat)
            take_request = TakePlayPileRequest(timed_out_player)
            game.process_playrequest(take_request, allow_when_hidden_available=True)
            self._clear_pending_hidden_take()
            if set_status_message:
                self.last_status_message = f"{player.display_name} disconnected after revealing a hidden card and took the play pile."
            summary = "took the play pile after revealing a hidden card"
        else:
            game.active_players.next()
            if set_status_message:
                self.last_status_message = (
                    f"{player.display_name} disconnected and missed their turn."
                )
        return summary

    async def _apply_disconnect_timeout(
        self,
        seat: int,
        expected_action: DisconnectAction | None = None,
    ):
        player = self._get_player_entry(seat)
        if player is None or player.connected:
            return

        action = expected_action or self._infer_disconnect_action(seat)
        if action is None:
            return
        if expected_action is not None and player.disconnect_action not in {None, expected_action}:
            return
        if (
            expected_action is not None
            and player.disconnect_action == expected_action
            and player.disconnect_deadline_at is not None
            and player.disconnect_deadline_at > _utc_now()
        ):
            return

        if action == DisconnectAction.AUTO_REMOVE_SETUP:
            self._remove_setup_player(
                seat,
                status_message=f"{player.display_name} disconnected and was removed before the game began.",
            )
            self._finalize_state_change()
            await self.broadcast_full_state()
            return

        if action != DisconnectAction.AUTO_PLAY_TURN:
            return

        resolution = self._resolve_current_offline_turn(seat)
        if resolution is None:
            self._sync_disconnect_policies()
            self._persist()
            return
        self._finalize_state_change()
        await self.broadcast_full_state()

    def kick_player(self, player_token: str, seat: int):
        player = self.get_player_by_token(player_token)
        if player.seat != self.host_seat:
            raise ValueError("Only the host can remove players.")
        if seat == self.host_seat:
            raise ValueError("The host cannot remove themselves.")

        target = self.get_player_by_seat(seat)
        if target.connected:
            raise ValueError("Only offline players can be removed.")

        if self.game_manager is None:
            self._remove_player_record(seat)
            self.last_status_message = f"{target.display_name} was removed while offline."
            self._finalize_state_change()
            return

        game = self.game_manager.game
        if game.state == GameState.PLAYERS_CHOOSE_PUBLIC_CARDS:
            self._remove_setup_player(
                seat,
                status_message=f"{target.display_name} was removed while offline before the game began.",
            )
            self._finalize_state_change()
            return

        turn_resolution = None
        if game.state == GameState.DURING_GAME and game.get_player().id_ == seat:
            turn_resolution = self._resolve_current_offline_turn(seat, set_status_message=False)

        self._remove_player_from_game(seat)
        self._remove_player_record(seat)
        if turn_resolution is not None:
            self.last_status_message = (
                f"{target.display_name} was removed while offline after they {turn_resolution}."
            )
        else:
            self.last_status_message = f"{target.display_name} was removed while offline."
        self._finalize_state_change()

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

    def _card_status_name(self, card: Card) -> str:
        if card.is_joker:
            return "joker"
        names = {
            11: "Jack",
            12: "Queen",
            13: "King",
            14: "Ace",
        }
        return names.get(int(card.rank), str(int(card.rank)))

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

        if (
            action_type not in {"play_private_cards", "resolve_joker", "play_hidden_card"}
            or played_rank is None
        ):
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
        elif self.game_manager.game.state == GameState.GAME_OVER:
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
                public_cards = [
                    self._serialize_card(card) for card in game_player.public_cards.cards
                ]
                hidden_cards_count = len(game_player.hidden_cards)
                private_cards_count = len(game_player.private_cards)

            players.append(
                PlayerSnapshot(
                    seat=player.seat,
                    display_name=player.display_name,
                    is_host=player.seat == self.host_seat,
                    is_connected=player.connected,
                    last_seen_at=player.last_seen.isoformat(),
                    disconnect_deadline_at=(
                        player.disconnect_deadline_at.isoformat()
                        if player.disconnect_deadline_at is not None
                        else None
                    ),
                    disconnect_action=player.disconnect_action,
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
                status_message=self.last_status_message,
                players=players,
                shoutout_presets=self._shoutout_presets(),
                rules=self._rules_snapshot(),
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
            current_valid_ranks=sort_ranks_by_precedence(self.game_manager.game.valid_ranks),
            status_message=self.last_status_message,
            pending_joker_selection=self.pending_joker_card is not None,
            cards_in_deck=len(self.game_manager.game.deck),
            play_pile=[
                self._serialize_card(card) for card in self.game_manager.game.play_pile.cards
            ],
            players=players,
            shoutout_presets=self._shoutout_presets(),
            rules=self._rules_snapshot(),
        )

    def build_private_state(self, seat: int) -> PrivateState:
        player = self._get_player_entry(seat)
        if player is None:
            return PrivateState(seat=seat, private_cards=[])

        cooldown_due_at = None
        if player.last_shoutout_at is not None:
            next_available_at = player.last_shoutout_at + timedelta(
                seconds=self.SHOUTOUT_COOLDOWN_SECONDS
            )
            if _utc_now() < next_available_at:
                cooldown_due_at = next_available_at

        game_player, _ = self._find_game_player(seat)
        return PrivateState(
            seat=seat,
            pending_joker_selection=self.pending_joker_seat == seat
            and self.pending_joker_card is not None,
            pending_joker_card=(
                self._serialize_card(self.pending_joker_card)
                if self.pending_joker_seat == seat and self.pending_joker_card is not None
                else None
            ),
            pending_hidden_take=self.pending_hidden_take_seat == seat,
            private_cards=(
                [
                    self._serialize_card(card)
                    for card in self._sort_private_cards(game_player.private_cards.cards)
                ]
                if game_player is not None
                else []
            ),
            shoutout_next_available_at=cooldown_due_at,
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

    def apply_action(self, player_token: str, action: ActionRequest) -> ShoutoutEvent | None:
        player = self.get_player_by_token(player_token)
        self._cancel_disconnect_timeout(player.seat)

        if action.type == "send_shoutout":
            self._sync_status()
            if self.status not in {
                SessionStatus.LOBBY,
                SessionStatus.IN_GAME,
                SessionStatus.GAME_OVER,
            }:
                raise ValueError(
                    "Shoutouts are only available in the lobby, during a game, or after it ends."
                )
            shoutout_event = self._build_shoutout_event(player, action.shoutout_key)
            self._finalize_state_change()
            return shoutout_event

        if self.game_manager is None:
            raise ValueError("Game has not started yet.")

        game = self.game_manager.game
        previous_play_pile = list(game.play_pile.cards)
        played_rank = None
        played_card_count = 0

        if self.pending_hidden_take_seat is not None:
            if player.seat != self.pending_hidden_take_seat:
                raise ValueError("Waiting for the active player to take the pile.")
            if action.type != "take_play_pile":
                raise ValueError("Take the pile before taking another action.")

        if self.pending_joker_card is not None:
            if player.seat != self.pending_joker_seat:
                raise ValueError(
                    "Waiting for the active player to finish resolving the revealed card."
                )
            if action.type != "resolve_joker":
                raise ValueError("Finish resolving the revealed card before taking another action.")

            request = RevealedCardsRequest(
                player=game.get_player(player.seat),
                cards=[self.pending_joker_card],
                choice=action.choice,
                joker_rank=action.joker_rank if self.pending_joker_card.is_joker else None,
            )
            game.process_revealed_request(request, already_on_pile=True)
            played_rank = (
                action.joker_rank
                if self.pending_joker_card.is_joker
                else int(self.pending_joker_card.rank)
            )
            played_card_count = 1
            self._clear_pending_joker()
        elif action.type == "play_hidden_card":
            hidden_request = HiddenCardRequest(game.get_player(player.seat))
            revealed_card = game.process_hidden_card(hidden_request)
            if revealed_card.is_joker:
                game.play_pile.put([revealed_card])
                self.pending_joker_seat = player.seat
                self.pending_joker_card = revealed_card
                self.last_status_message = f"{player.display_name} revealed a joker."
            else:
                game.play_pile.put([revealed_card])
                if int(revealed_card.rank) == int(SpecialRank.HIGHLOW):
                    if int(revealed_card.rank) in game.valid_ranks:
                        self.pending_joker_seat = player.seat
                        self.pending_joker_card = revealed_card
                        self.last_status_message = f"{player.display_name} revealed {self._card_status_name(revealed_card)}."
                    else:
                        self.pending_hidden_take_seat = player.seat
                        self.last_status_message = f"{player.display_name} revealed {self._card_status_name(revealed_card)} and must take the pile."
                    self._finalize_state_change()
                    return
                if int(revealed_card.rank) in game.valid_ranks:
                    request = RevealedCardsRequest(
                        player=game.get_player(player.seat), cards=[revealed_card]
                    )
                    game.process_revealed_request(request, already_on_pile=True)
                    played_rank = int(revealed_card.rank)
                    played_card_count = 1
                    current_play_pile = list(game.play_pile.cards)
                    self.last_status_message = self._build_status_message(
                        player=player,
                        action_type="play_hidden_card",
                        played_rank=played_rank,
                        choice=action.choice,
                        previous_play_pile=previous_play_pile,
                        current_play_pile=current_play_pile,
                        played_card_count=played_card_count,
                    )
                    self._finalize_state_change()
                    return
                self.pending_hidden_take_seat = player.seat
                self.last_status_message = f"{player.display_name} revealed {self._card_status_name(revealed_card)} and must take the pile."
            self._finalize_state_change()
            return
        else:
            if action.type == "take_play_pile":
                request = TakePlayPileRequest(game.get_player(player.seat))
                allow_optional_take = (
                    self.settings.allow_optional_take_pile
                    and self.pending_hidden_take_seat != player.seat
                )
                game.process_playrequest(
                    request,
                    allow_when_hidden_available=(
                        self.pending_hidden_take_seat == player.seat or allow_optional_take
                    ),
                    allow_optional_take=allow_optional_take,
                )
                self._clear_pending_hidden_take()
            else:
                request = self._request_from_action(player, action)
                self.game_manager.process_request(request)
            played_rank = (
                action.joker_rank
                if action.joker_rank is not None
                else (
                    action.cards[0].effective_rank or action.cards[0].rank if action.cards else None
                )
            )
            played_card_count = len(action.cards)

        current_play_pile = list(game.play_pile.cards)
        self.last_status_message = self._build_status_message(
            player=player,
            action_type=action.type,
            played_rank=played_rank,
            choice=action.choice,
            previous_play_pile=previous_play_pile,
            current_play_pile=current_play_pile,
            played_card_count=played_card_count,
        )
        self._finalize_state_change()

    async def connect(self, player_token: str, websocket: WebSocket):
        player = self.get_player_by_token(player_token)
        self._cancel_disconnect_timeout(player.seat)
        await websocket.accept()
        player.mark_connected(websocket)
        self._finalize_state_change()
        await self.send_full_state(player)
        await self.broadcast_snapshot(exclude_seat=player.seat)

    async def disconnect(self, player_token: str):
        player = self.get_player_by_token(player_token)
        self._handle_player_disconnect(player)
        await self.broadcast_snapshot()

    async def _safe_send(self, websocket: Optional[WebSocket], payload: dict) -> bool:
        if websocket is None:
            return False
        if websocket.application_state == WebSocketState.DISCONNECTED:
            return False
        try:
            await websocket.send_json(jsonable_encoder(payload))
            return True
        except Exception:
            return False

    async def send_full_state(self, player: SessionPlayer):
        snapshot_event = SessionSnapshotEvent(data=self.build_snapshot()).dict()
        private_state_event = PrivateStateEvent(data=self.build_private_state(player.seat)).dict()
        if not await self._safe_send(player.websocket, snapshot_event):
            self._handle_player_disconnect(player)
            return
        if not await self._safe_send(player.websocket, private_state_event):
            self._handle_player_disconnect(player)

    async def send_private_state(self, player: SessionPlayer):
        private_state_event = PrivateStateEvent(data=self.build_private_state(player.seat)).dict()
        if not await self._safe_send(player.websocket, private_state_event):
            self._handle_player_disconnect(player)

    async def broadcast_snapshot(self, exclude_seat: int | None = None):
        snapshot_event = SessionSnapshotEvent(data=self.build_snapshot()).dict()
        for player in self.players:
            if player.seat == exclude_seat:
                continue
            if player.websocket is not None:
                sent = await self._safe_send(player.websocket, snapshot_event)
                if not sent:
                    self._handle_player_disconnect(player)

    async def broadcast_full_state(self):
        for player in self.players:
            if player.websocket is not None:
                await self.send_full_state(player)

    async def broadcast_shoutout(self, shoutout_event: ShoutoutEvent):
        payload = shoutout_event.dict()
        for player in self.players:
            if player.websocket is not None:
                sent = await self._safe_send(player.websocket, payload)
                if not sent:
                    self._handle_player_disconnect(player)

    async def send_error(self, player_token: str, message: str):
        player = self.get_player_by_token(player_token)
        if player.websocket is not None:
            sent = await self._safe_send(player.websocket, ActionErrorEvent(message=message).dict())
            if not sent:
                self._handle_player_disconnect(player)


class GameSessionManager:
    def __init__(self, store: SQLiteSessionStore | None = None):
        self.store = store or SQLiteSessionStore()
        self.sessions = SessionCache(self._clear_all_sessions)
        self.store.mark_all_players_disconnected()

    def _record_metric(self, label: str, callback: Callable, *args, **kwargs):
        try:
            callback(*args, **kwargs)
        except Exception:
            logger.exception("Failed to record %s.", label)

    def note_user_seen(self, user_id: str | None, seen_at: datetime | None = None):
        if not user_id:
            return
        self._record_metric(
            "user activity metric",
            self.store.ensure_user_seen,
            user_id,
            seen_at or _utc_now(),
        )

    def note_lobby_created(
        self,
        invite_code: str,
        creator_user_id: str | None = None,
        created_at: datetime | None = None,
    ):
        self._record_metric(
            "lobby creation metric",
            self.store.record_lobby_created,
            invite_code,
            created_at or _utc_now(),
            creator_user_id,
        )

    def note_game_started(
        self,
        game_id: int,
        invite_code: str,
        player_count: int,
        started_at: datetime | None = None,
    ):
        self._record_metric(
            "game start metric",
            self.store.record_game_started,
            game_id,
            invite_code,
            started_at or _utc_now(),
            player_count,
        )

    def note_game_completed(
        self,
        game_id: int,
        invite_code: str,
        player_count: int,
        completed_at: datetime | None = None,
    ):
        self._record_metric(
            "game completion metric",
            self.store.record_game_completed,
            game_id,
            invite_code,
            completed_at or _utc_now(),
            player_count,
        )

    def note_game_abandoned(
        self,
        game_id: int,
        invite_code: str,
        player_count: int,
        abandoned_at: datetime | None = None,
    ):
        self._record_metric(
            "game abandonment metric",
            self.store.record_game_abandoned,
            game_id,
            invite_code,
            abandoned_at or _utc_now(),
            player_count,
        )

    def _record_session_metrics(self, session: "GameSession"):
        if session.game_manager is None:
            return

        game = session.game_manager.game
        if game.state == GameState.DURING_GAME:
            self.note_game_started(game.game_id, session.invite_code, len(session.players))
            return

        if game.state == GameState.GAME_OVER:
            self.note_game_started(game.game_id, session.invite_code, len(session.players))
            self.note_game_completed(game.game_id, session.invite_code, len(session.players))

    def get_stats(self, days: int = 30) -> dict:
        return self.store.build_stats(days=days)

    def _clear_all_sessions(self):
        for session in list(self.sessions.values()):
            session.shutdown()
        self.store.clear_all()

    def _serialize_card(self, card: Card) -> dict:
        return {
            "rank": int(card.rank),
            "suit": int(card.suit),
            "effective_rank": card.effective_rank,
            "high_low_choice": card.high_low_choice,
        }

    def _deserialize_card(self, data: dict) -> Card:
        return Card(
            rank=data["rank"],
            suit=data["suit"],
            effective_rank=data.get("effective_rank"),
            high_low_choice=data.get("high_low_choice"),
        )

    def _serialize_game_state(self, session: GameSession) -> dict | None:
        if session.game_manager is None:
            return None
        game = session.game_manager.game
        game_players = {player.id_: player for player in game.active_players}
        game_players.update({player.id_: player for player in game.ranking})
        return {
            "schema_version": 1,
            "game_id": game.game_id,
            "state": str(game.state),
            "valid_ranks": sorted(int(rank) for rank in game.valid_ranks),
            "deck": [self._serialize_card(card) for card in game.deck.cards],
            "play_pile": [self._serialize_card(card) for card in game.play_pile.cards],
            "active_player_order": [
                player.id_ for player in game.active_players.get_ordered_list()
            ],
            "ranking": [player.id_ for player in game.ranking],
            "players": {
                str(seat): {
                    "public_cards_were_selected": player.public_cards_were_selected,
                    "private_cards": [self._serialize_card(card) for card in player.private_cards],
                    "public_cards": [self._serialize_card(card) for card in player.public_cards],
                    "hidden_cards": [self._serialize_card(card) for card in player.hidden_cards],
                }
                for seat, player in game_players.items()
            },
        }

    def _deserialize_game_state(self, game_state: dict | None) -> GameManager | None:
        if game_state is None:
            return None
        players_by_seat: dict[int, Player] = {}
        for seat_text, player_state in game_state["players"].items():
            seat = int(seat_text)
            player = Player(seat)
            player.public_cards_were_selected = player_state["public_cards_were_selected"]
            player.private_cards = SetOfCards(
                [self._deserialize_card(card) for card in player_state["private_cards"]]
            )
            player.hidden_cards = SetOfCards(
                [self._deserialize_card(card) for card in player_state["hidden_cards"]]
            )
            player._public_cards = SetOfCards(
                [self._deserialize_card(card) for card in player_state["public_cards"]]
            )
            players_by_seat[seat] = player

        active_players = [players_by_seat[seat] for seat in game_state["active_player_order"]]
        game = Game(
            players=active_players,
            deck=PileOfCards([self._deserialize_card(card) for card in game_state["deck"]]),
            play_pile=PileOfCards(
                [self._deserialize_card(card) for card in game_state["play_pile"]]
            ),
            game_id=game_state["game_id"],
            state=GameState(game_state["state"]),
        )
        game.active_players = CircularDoublyLinkedList(active_players)
        game.ranking = [players_by_seat[seat] for seat in game_state["ranking"]]
        game.valid_ranks = {int(rank) for rank in game_state["valid_ranks"]}
        manager = GameManager.__new__(GameManager)
        manager.game = game
        return manager

    def _serialize_session_record(self, session: GameSession) -> dict:
        return {
            "invite_code": session.invite_code,
            "status": session.status,
            "host_seat": session.host_seat,
            "host_token": session.host_token,
            "last_status_message": session.last_status_message,
            "pending_joker_seat": session.pending_joker_seat,
            "pending_joker_card": (
                self._serialize_card(session.pending_joker_card)
                if session.pending_joker_card is not None
                else None
            ),
            "pending_hidden_take_seat": session.pending_hidden_take_seat,
            "disconnect_timeout_seconds": session.active_turn_disconnect_grace_seconds,
            "last_activity_at": session.last_activity_at.isoformat(),
            "settings": {
                "sort_hand_cards": session.settings.sort_hand_cards,
                "allow_optional_take_pile": session.settings.allow_optional_take_pile,
            },
            "players": [
                {
                    "seat": player.seat,
                    "display_name": player.display_name,
                    "token": player.token,
                    "connected": player.connected,
                    "last_seen": player.last_seen.isoformat(),
                    "disconnect_deadline_at": (
                        player.disconnect_deadline_at.isoformat()
                        if player.disconnect_deadline_at is not None
                        else None
                    ),
                    "disconnect_action": (
                        player.disconnect_action.value
                        if player.disconnect_action is not None
                        else None
                    ),
                }
                for player in session.players
            ],
            "game_state": self._serialize_game_state(session),
        }

    def _deserialize_session_record(self, record: dict) -> GameSession:
        host_player = next(
            (player for player in record["players"] if player["seat"] == record["host_seat"]),
            None,
        )
        if host_player is None:
            raise ValueError(f"Corrupt session record for invite {record['invite_code']}.")
        session = GameSession(
            invite_code=record["invite_code"],
            host_name=host_player["display_name"],
            on_reap=self._reap_session,
            on_change=self._save_session,
        )
        session.players = [
            SessionPlayer(
                seat=player["seat"],
                display_name=player["display_name"],
                token=player["token"],
                connected=player["connected"],
                last_seen=datetime.fromisoformat(player["last_seen"]),
                disconnect_deadline_at=(
                    datetime.fromisoformat(player["disconnect_deadline_at"])
                    if player.get("disconnect_deadline_at")
                    else None
                ),
                disconnect_action=(
                    DisconnectAction(player["disconnect_action"])
                    if player.get("disconnect_action")
                    else None
                ),
            )
            for player in record["players"]
        ]
        session.host_seat = record["host_seat"]
        session.host_token = record["host_token"]
        session.status = SessionStatus(record["status"])
        session.last_status_message = record["last_status_message"]
        session.pending_joker_seat = record["pending_joker_seat"]
        session.pending_joker_card = (
            self._deserialize_card(record["pending_joker_card"])
            if record["pending_joker_card"] is not None
            else None
        )
        session.pending_hidden_take_seat = record["pending_hidden_take_seat"]
        session.active_turn_disconnect_grace_seconds = record.get(
            "disconnect_timeout_seconds", session.active_turn_disconnect_grace_seconds
        )
        session.last_activity_at = datetime.fromisoformat(record["last_activity_at"])
        session.settings = SessionSettings(**record["settings"])
        session.game_manager = self._deserialize_game_state(record["game_state"])
        return session

    def _save_session(self, session: GameSession):
        self.store.save_session_record(self._serialize_session_record(session))
        self._record_session_metrics(session)

    def _reap_session(self, invite_code: str, session: GameSession | None = None):
        cached_session = self.sessions.pop(invite_code, None)
        session = session or cached_session
        if session is not None:
            self._record_session_metrics(session)
            if (
                session.game_manager is not None
                and session.game_manager.game.state == GameState.DURING_GAME
            ):
                self.note_game_abandoned(
                    session.game_manager.game.game_id,
                    session.invite_code,
                    len(session.players),
                )
            session.shutdown()
        self.store.delete_session(invite_code)

    def reap_expired_sessions(self):
        expired_sessions: dict[str, GameSession | None] = {}
        for invite_code, session in self.sessions.items():
            if session.is_expired():
                expired_sessions[invite_code] = session
        for record in self.store.list_session_records():
            invite_code = record["invite_code"]
            if invite_code in self.sessions:
                continue
            try:
                session = self._deserialize_session_record(record)
            except ValueError:
                expired_sessions[invite_code] = None
                continue
            if session.is_expired():
                expired_sessions[invite_code] = session
        for invite_code, session in expired_sessions.items():
            self._reap_session(invite_code, session)

    def _generate_invite_code(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = "".join(secrets.choice(alphabet) for _ in range(6))
            if code not in self.sessions and not self.store.invite_code_exists(code):
                return code

    def create_session(self, display_name: str, creator_user_id: str | None = None) -> GameSession:
        self.reap_expired_sessions()
        session = GameSession(
            invite_code=self._generate_invite_code(),
            host_name=display_name,
            on_reap=self._reap_session,
            on_change=self._save_session,
        )
        self.sessions[session.invite_code] = session
        session._sync_reap_schedule()
        self._save_session(session)
        self.note_user_seen(creator_user_id)
        self.note_lobby_created(session.invite_code, creator_user_id=creator_user_id)
        return session

    def get_session(self, invite_code: str) -> GameSession:
        self.reap_expired_sessions()
        normalized_invite_code = invite_code.upper()
        session = self.sessions.get(normalized_invite_code)
        if session is None:
            record = self.store.load_session_record(normalized_invite_code)
            if record is None:
                raise ValueError("Game not found.")
            session = self._deserialize_session_record(record)
            if session.is_expired():
                self._reap_session(normalized_invite_code)
                raise ValueError("Game not found.")
            self.sessions[normalized_invite_code] = session
            session._sync_disconnect_policies()
            self._save_session(session)
            session._sync_reap_schedule()
        return session
