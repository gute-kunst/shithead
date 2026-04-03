from __future__ import annotations

from dataclasses import dataclass

from pyshithead.models.game import (
    ALL_RANKS,
    JOKER_RANK,
    Card,
    GameState,
    PileOfCards,
    RankEvent,
    RankType,
    SetOfCards,
    SpecialRank,
    Suit,
)
from pyshithead.models.session import GameSession, GameSessionManager
from pyshithead.models.session.models import SessionStatus

DEBUG_PRESET_NAMES = (
    "lobby-2p",
    "choose-public",
    "normal-turn",
    "host-specials",
    "host-specials-lock",
    "host-turn-15",
    "hidden-reveal",
    "hidden-take",
    "revealed-joker",
    "revealed-seven",
    "game-over",
)


@dataclass(frozen=True)
class DebugSeatLink:
    seat: int
    display_name: str
    token: str
    is_host: bool


@dataclass(frozen=True)
class DebugPresetSeed:
    preset_name: str
    session: GameSession
    seats: tuple[DebugSeatLink, ...]


def _session_players(session: GameSession) -> tuple[DebugSeatLink, ...]:
    return tuple(
        DebugSeatLink(
            seat=player.seat,
            display_name=player.display_name,
            token=player.token,
            is_host=player.seat == session.host_seat,
        )
        for player in sorted(session.players, key=lambda entry: entry.seat)
    )


def _base_lobby_session(manager: GameSessionManager, names: tuple[str, ...]) -> GameSession:
    session = manager.create_session(names[0])
    for name in names[1:]:
        session.join(name)
    return session


def _base_started_session(manager: GameSessionManager, names: tuple[str, ...]) -> GameSession:
    session = _base_lobby_session(manager, names)
    session.start(session.host_token)
    return session


def _set_player_cards(
    session: GameSession,
    seat: int,
    *,
    private: list[Card] | None = None,
    public: list[Card] | None = None,
    hidden: list[Card] | None = None,
):
    player = session.game_manager.game.get_player(seat)
    if private is not None:
        player.private_cards = SetOfCards(private)
    if public is not None:
        player.public_cards = SetOfCards(public)
    if hidden is not None:
        player.hidden_cards = SetOfCards(hidden)
    return player


def _prepare_during_game(session: GameSession):
    game = session.game_manager.game
    game.state = GameState.DURING_GAME
    game.deck = PileOfCards()
    session.status = SessionStatus.IN_GAME
    session.last_status_message = None
    session.pending_joker_seat = None
    session.pending_joker_card = None
    session.pending_hidden_take_seat = None
    return game


def _valid_ranks_for_top_rank(rank: int) -> set[int]:
    return RankEvent(RankType.TOPRANK, rank).get_valid_ranks(set(ALL_RANKS))


def _build_lobby_2p(manager: GameSessionManager) -> GameSession:
    return _base_lobby_session(manager, ("Host", "Guest"))


def _build_choose_public(manager: GameSessionManager) -> GameSession:
    return _base_started_session(manager, ("Host", "Guest"))


def _build_normal_turn(manager: GameSessionManager) -> GameSession:
    session = _base_started_session(manager, ("Host", "Guest"))
    game = _prepare_during_game(session)
    game.play_pile = PileOfCards([Card(6, Suit.HEART)])
    game.valid_ranks = _valid_ranks_for_top_rank(6)
    _set_player_cards(
        session,
        0,
        private=[Card(9, Suit.HEART), Card(9, Suit.CLOVERS), Card(12, Suit.PIKES)],
        public=[],
        hidden=[Card(4, Suit.TILES), Card(7, Suit.CLOVERS), Card(11, Suit.HEART)],
    )
    _set_player_cards(
        session,
        1,
        private=[Card(10, Suit.CLOVERS), Card(3, Suit.HEART)],
        public=[],
        hidden=[Card(6, Suit.TILES), Card(8, Suit.HEART), Card(13, Suit.CLOVERS)],
    )
    return session


def _build_host_specials(manager: GameSessionManager) -> GameSession:
    session = _base_started_session(manager, ("Host", "Guest"))
    game = _prepare_during_game(session)
    game.play_pile = PileOfCards()
    game.valid_ranks = set(range(2, 15))
    _set_player_cards(
        session,
        0,
        private=[
            Card(SpecialRank.RESET, Suit.HEART),
            Card(SpecialRank.INVISIBLE, Suit.CLOVERS),
            Card(SpecialRank.HIGHLOW, Suit.PIKES),
            Card(SpecialRank.SKIP, Suit.TILES),
            Card(SpecialRank.BURN, Suit.HEART),
            Card(JOKER_RANK, Suit.JOKER_RED),
        ],
        public=[],
        hidden=[Card(4, Suit.TILES), Card(11, Suit.HEART), Card(13, Suit.CLOVERS)],
    )
    _set_player_cards(
        session,
        1,
        private=[Card(9, Suit.HEART), Card(12, Suit.CLOVERS)],
        public=[],
        hidden=[Card(6, Suit.TILES), Card(8, Suit.HEART), Card(14, Suit.PIKES)],
    )
    session.last_status_message = "Host has a debug hand with all special ranks."
    return session


def _build_host_specials_lock(manager: GameSessionManager) -> GameSession:
    session = _base_started_session(manager, ("Host", "Guest"))
    _set_player_cards(
        session,
        0,
        private=[
            Card(SpecialRank.RESET, Suit.HEART),
            Card(SpecialRank.INVISIBLE, Suit.CLOVERS),
            Card(SpecialRank.HIGHLOW, Suit.PIKES),
            Card(SpecialRank.SKIP, Suit.TILES),
            Card(SpecialRank.BURN, Suit.HEART),
            Card(JOKER_RANK, Suit.JOKER_RED),
        ],
        public=[],
        hidden=[Card(4, Suit.TILES), Card(11, Suit.HEART), Card(13, Suit.CLOVERS)],
    )
    _set_player_cards(
        session,
        1,
        private=[Card(9, Suit.HEART), Card(12, Suit.CLOVERS), Card(14, Suit.PIKES)],
        public=[],
        hidden=[Card(6, Suit.TILES), Card(8, Suit.HEART), Card(13, Suit.PIKES)],
    )
    session.last_status_message = "Host must lock public cards from a debug hand with all special ranks."
    return session


def _build_host_turn_15(manager: GameSessionManager) -> GameSession:
    session = _base_started_session(manager, ("Host", "Guest"))
    game = _prepare_during_game(session)
    game.play_pile = PileOfCards([Card(6, Suit.HEART)])
    game.valid_ranks = _valid_ranks_for_top_rank(6)
    _set_player_cards(
        session,
        0,
        private=[
            Card(3, Suit.HEART),
            Card(3, Suit.CLOVERS),
            Card(4, Suit.PIKES),
            Card(6, Suit.HEART),
            Card(7, Suit.CLOVERS),
            Card(8, Suit.TILES),
            Card(9, Suit.HEART),
            Card(9, Suit.PIKES),
            Card(11, Suit.TILES),
            Card(12, Suit.CLOVERS),
            Card(13, Suit.HEART),
            Card(14, Suit.PIKES),
            Card(SpecialRank.RESET, Suit.CLOVERS),
            Card(SpecialRank.SKIP, Suit.HEART),
            Card(JOKER_RANK, Suit.JOKER_RED),
        ],
        public=[],
        hidden=[],
    )
    _set_player_cards(
        session,
        1,
        private=[Card(9, Suit.CLOVERS), Card(12, Suit.HEART), Card(13, Suit.PIKES)],
        public=[],
        hidden=[],
    )
    session.last_status_message = "Host is up with a 15-card hand."
    return session


def _build_hidden_reveal(manager: GameSessionManager) -> GameSession:
    session = _base_started_session(manager, ("Host", "Guest"))
    game = _prepare_during_game(session)
    game.play_pile = PileOfCards([Card(6, Suit.HEART)])
    game.valid_ranks = _valid_ranks_for_top_rank(6)
    _set_player_cards(
        session,
        0,
        private=[],
        public=[],
        hidden=[Card(9, Suit.CLOVERS), Card(4, Suit.HEART), Card(11, Suit.TILES)],
    )
    _set_player_cards(
        session,
        1,
        private=[Card(12, Suit.HEART), Card(3, Suit.CLOVERS)],
        public=[],
        hidden=[Card(6, Suit.TILES), Card(8, Suit.HEART), Card(13, Suit.PIKES)],
    )
    return session


def _build_hidden_take(manager: GameSessionManager) -> GameSession:
    session = _base_started_session(manager, ("Host", "Guest"))
    game = _prepare_during_game(session)
    game.play_pile = PileOfCards([Card(4, Suit.CLOVERS), Card(9, Suit.HEART)])
    game.valid_ranks = {10, 11, 12}
    _set_player_cards(
        session,
        0,
        private=[],
        public=[],
        hidden=[Card(6, Suit.HEART)],
    )
    _set_player_cards(
        session,
        1,
        private=[Card(12, Suit.HEART), Card(3, Suit.CLOVERS)],
        public=[],
        hidden=[Card(6, Suit.TILES), Card(8, Suit.HEART), Card(13, Suit.PIKES)],
    )
    session.pending_hidden_take_seat = 0
    session.last_status_message = "Host revealed 4 and must take the pile."
    return session


def _build_revealed_joker(manager: GameSessionManager) -> GameSession:
    session = _base_started_session(manager, ("Host", "Guest"))
    game = _prepare_during_game(session)
    game.play_pile = PileOfCards([Card(JOKER_RANK, Suit.JOKER_RED)])
    game.valid_ranks = set(range(2, 15))
    _set_player_cards(session, 0, private=[], public=[], hidden=[Card(6, Suit.HEART)])
    _set_player_cards(
        session,
        1,
        private=[Card(9, Suit.HEART), Card(12, Suit.CLOVERS)],
        public=[],
        hidden=[Card(6, Suit.TILES), Card(8, Suit.HEART), Card(13, Suit.PIKES)],
    )
    session.pending_joker_seat = 0
    session.pending_joker_card = Card(JOKER_RANK, Suit.JOKER_RED)
    session.last_status_message = "Host revealed a joker."
    return session


def _build_revealed_seven(manager: GameSessionManager) -> GameSession:
    session = _base_started_session(manager, ("Host", "Guest"))
    game = _prepare_during_game(session)
    game.play_pile = PileOfCards([Card(SpecialRank.HIGHLOW, Suit.HEART)])
    game.valid_ranks = set(range(2, 15))
    _set_player_cards(session, 0, private=[], public=[], hidden=[Card(6, Suit.HEART)])
    _set_player_cards(
        session,
        1,
        private=[Card(9, Suit.HEART), Card(12, Suit.CLOVERS)],
        public=[],
        hidden=[Card(6, Suit.TILES), Card(8, Suit.HEART), Card(13, Suit.PIKES)],
    )
    session.pending_joker_seat = 0
    session.pending_joker_card = Card(SpecialRank.HIGHLOW, Suit.HEART)
    session.last_status_message = "Host revealed 7."
    return session


def _build_game_over(manager: GameSessionManager) -> GameSession:
    session = _base_started_session(manager, ("Host", "Guest"))
    game = _prepare_during_game(session)
    winner = game.get_player(0)
    winner.private_cards = SetOfCards()
    winner.public_cards = SetOfCards()
    winner.hidden_cards = SetOfCards()
    game.ranking = [winner]
    game.active_players.remove_node(winner)
    game.check_for_game_over()
    session.last_status_message = "Host won the debug game."
    session.status = SessionStatus.GAME_OVER
    return session


PRESET_BUILDERS = {
    "lobby-2p": _build_lobby_2p,
    "choose-public": _build_choose_public,
    "normal-turn": _build_normal_turn,
    "host-specials": _build_host_specials,
    "host-specials-lock": _build_host_specials_lock,
    "host-turn-15": _build_host_turn_15,
    "hidden-reveal": _build_hidden_reveal,
    "hidden-take": _build_hidden_take,
    "revealed-joker": _build_revealed_joker,
    "revealed-seven": _build_revealed_seven,
    "game-over": _build_game_over,
}


def seed_debug_preset(manager: GameSessionManager, preset_name: str) -> DebugPresetSeed:
    builder = PRESET_BUILDERS.get(preset_name)
    if builder is None:
        raise ValueError(
            f"Unknown debug preset '{preset_name}'. Available presets: {', '.join(DEBUG_PRESET_NAMES)}"
        )
    manager.sessions.clear()
    session = builder(manager)
    return DebugPresetSeed(
        preset_name=preset_name,
        session=session,
        seats=_session_players(session),
    )
