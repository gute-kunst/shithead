import pytest
from fastapi.testclient import TestClient

from pyshithead.main import app, session_manager
from pyshithead.models.game import (
    ALL_RANKS,
    Card,
    GameState,
    JOKER_RANK,
    PileOfCards,
    RankEvent,
    RankType,
    SetOfCards,
    SpecialRank,
    Suit,
)
from pyshithead.models.game.errors import CardsNotEligibleOnPlayPileError
from pyshithead.models.session.models import ActionRequest, CardModel


def receive_until_types(websocket, expected_types: set[str], limit: int = 8):
    messages = {}
    for _ in range(limit):
        message = websocket.receive_json()
        messages[message["type"]] = message
        if expected_types.issubset(messages.keys()):
            return messages
    raise AssertionError(f"Did not receive expected messages: {expected_types}")


def create_game(client: TestClient, display_name: str):
    response = client.post("/api/games", json={"display_name": display_name})
    assert response.status_code == 200
    return response.json()


def join_game(client: TestClient, invite_code: str, display_name: str):
    response = client.post(f"/api/games/{invite_code}/join", json={"display_name": display_name})
    assert response.status_code == 200
    return response.json()


def start_game(client: TestClient, invite_code: str, player_token: str):
    response = client.post(
        f"/api/games/{invite_code}/start",
        json={"player_token": player_token},
    )
    assert response.status_code == 200
    return response.json()


def restore_session(client: TestClient, invite_code: str, player_token: str):
    return client.post(
        f"/api/games/{invite_code}/restore",
        json={"player_token": player_token},
    )


def private_card_signature(cards):
    return [
        (
            card["rank"] if isinstance(card, dict) else card.rank,
            card["suit"] if isinstance(card, dict) else card.suit,
            card.get("effective_rank") if isinstance(card, dict) else getattr(card, "effective_rank", None),
        )
        for card in cards
    ]


def test_create_and_join_alpha_lobby():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        root = client.get("/")
        assert root.status_code == 200
        assert "Create a table" in root.text
        assert "Alpha notice" in root.text

        health = client.get("/healthz")
        assert health.status_code == 200
        assert health.json() == {"ok": True}

        host = create_game(client, "Host")
        invite_code = host["invite_code"]
        assert host["seat"] == 0
        assert host["snapshot"]["status"] == "LOBBY"
        assert host["snapshot"]["players"][0]["display_name"] == "Host"

        guest = join_game(client, invite_code, "Guest")
        assert guest["seat"] == 1

        state = client.get(f"/api/games/{invite_code}")
        assert state.status_code == 200
        snapshot = state.json()["data"]
        assert snapshot["status"] == "LOBBY"
        assert [player["display_name"] for player in snapshot["players"]] == ["Host", "Guest"]


def test_start_game_and_reconnect_with_same_token():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        guest = join_game(client, host["invite_code"], "Guest")

        host_path = f"/api/games/{host['invite_code']}/ws?token={host['player_token']}"
        guest_path = f"/api/games/{host['invite_code']}/ws?token={guest['player_token']}"

        with client.websocket_connect(host_path) as host_ws:
            host_messages = receive_until_types(host_ws, {"session_snapshot", "private_state"})
            assert host_messages["session_snapshot"]["data"]["status"] == "LOBBY"

            with client.websocket_connect(guest_path) as guest_ws:
                guest_messages = receive_until_types(guest_ws, {"session_snapshot", "private_state"})
                assert guest_messages["session_snapshot"]["data"]["players"][1]["display_name"] == "Guest"

                join_notice = host_ws.receive_json()
                assert join_notice["type"] == "session_snapshot"
                assert join_notice["data"]["players"][1]["is_connected"] is True

                start_payload = start_game(client, host["invite_code"], host["player_token"])
                assert start_payload["data"]["status"] == "IN_GAME"

                host_started = receive_until_types(host_ws, {"session_snapshot", "private_state"})
                guest_started = receive_until_types(guest_ws, {"session_snapshot", "private_state"})
                assert host_started["session_snapshot"]["data"]["game_state"] == "PLAYERS_CHOOSE_PUBLIC_CARDS"
                assert len(host_started["private_state"]["data"]["private_cards"]) == 6
                assert guest_started["private_state"]["data"]["seat"] == 1

            disconnect_notice = host_ws.receive_json()
            assert disconnect_notice["type"] == "session_snapshot"
            guest_after_disconnect = disconnect_notice["data"]["players"][1]
            assert guest_after_disconnect["is_connected"] is False

            with client.websocket_connect(guest_path) as guest_ws_reconnected:
                reconnected = receive_until_types(
                    guest_ws_reconnected,
                    {"session_snapshot", "private_state"},
                )
                assert reconnected["private_state"]["data"]["seat"] == 1

                reconnect_notice = host_ws.receive_json()
                assert reconnect_notice["type"] == "session_snapshot"
                guest_after_reconnect = reconnect_notice["data"]["players"][1]
                assert guest_after_reconnect["is_connected"] is True


def test_fresh_started_game_has_empty_play_pile_during_public_card_selection():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")

        started = start_game(client, host["invite_code"], host["player_token"])

        assert started["data"]["status"] == "IN_GAME"
        assert started["data"]["game_state"] == "PLAYERS_CHOOSE_PUBLIC_CARDS"
        assert started["data"]["play_pile"] == []

        state = client.get(f"/api/games/{host['invite_code']}")
        assert state.status_code == 200
        snapshot = state.json()["data"]
        assert snapshot["game_state"] == "PLAYERS_CHOOSE_PUBLIC_CARDS"
        assert snapshot["play_pile"] == []


def test_restore_returns_player_scoped_private_state():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        guest = join_game(client, host["invite_code"], "Guest")
        start_game(client, host["invite_code"], host["player_token"])

        restored = restore_session(client, host["invite_code"], guest["player_token"])
        assert restored.status_code == 200

        payload = restored.json()
        assert payload["invite_code"] == host["invite_code"]
        assert payload["seat"] == 1
        assert payload["snapshot"]["status"] == "IN_GAME"
        assert payload["snapshot"]["players"][1]["display_name"] == "Guest"
        assert payload["private_state"]["seat"] == 1
        assert len(payload["private_state"]["private_cards"]) == 6


def test_private_state_sorts_hand_cards_by_rank_with_jokers_last():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")

        session = session_manager.get_session(host["invite_code"])
        assert session.settings.sort_hand_cards is True
        session.start(host["player_token"])

        host_player = session.game_manager.game.get_player(0)
        host_player.private_cards = SetOfCards(
            [
                Card(JOKER_RANK, Suit.JOKER_BLACK),
                Card(12, Suit.HEART),
                Card(13, Suit.TILES),
                Card(3, Suit.CLOVERS),
                Card(13, Suit.HEART),
                Card(JOKER_RANK, Suit.JOKER_RED),
            ]
        )

        private_state = session.build_private_state(0)

        assert private_card_signature(private_state.private_cards) == [
            (3, Suit.CLOVERS, None),
            (13, Suit.TILES, None),
            (13, Suit.HEART, None),
            (12, Suit.HEART, None),
            (JOKER_RANK, Suit.JOKER_RED, None),
            (JOKER_RANK, Suit.JOKER_BLACK, None),
        ]


def test_restore_returns_sorted_private_cards():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        guest = join_game(client, host["invite_code"], "Guest")
        start_game(client, host["invite_code"], host["player_token"])

        session = session_manager.get_session(host["invite_code"])
        guest_player = session.game_manager.game.get_player(1)
        guest_player.private_cards = SetOfCards(
            [
                Card(JOKER_RANK, Suit.JOKER_BLACK),
                Card(14, Suit.CLOVERS),
                Card(11, Suit.HEART),
                Card(13, Suit.CLOVERS),
                Card(12, Suit.TILES),
                Card(4, Suit.PIKES),
            ]
        )

        restored = restore_session(client, host["invite_code"], guest["player_token"])

        assert restored.status_code == 200
        assert private_card_signature(restored.json()["private_state"]["private_cards"]) == [
            (4, Suit.PIKES, None),
            (11, Suit.HEART, None),
            (13, Suit.CLOVERS, None),
            (12, Suit.TILES, None),
            (14, Suit.CLOVERS, None),
            (JOKER_RANK, Suit.JOKER_BLACK, None),
        ]


def test_restore_rejects_unknown_player_token():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")

        restored = restore_session(client, host["invite_code"], "invalid-token")
        assert restored.status_code == 401
        assert restored.json() == {"detail": "Unknown player token."}


def test_restore_returns_not_found_for_missing_game():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        restored = restore_session(client, "MISSING", "invalid-token")
        assert restored.status_code == 404
        assert restored.json() == {"detail": "Game not found."}


def test_choose_public_cards_over_new_websocket_flow():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        guest = join_game(client, host["invite_code"], "Guest")
        host_path = f"/api/games/{host['invite_code']}/ws?token={host['player_token']}"
        guest_path = f"/api/games/{host['invite_code']}/ws?token={guest['player_token']}"

        with client.websocket_connect(host_path) as host_ws:
            receive_until_types(host_ws, {"session_snapshot", "private_state"})

            with client.websocket_connect(guest_path) as guest_ws:
                receive_until_types(guest_ws, {"session_snapshot", "private_state"})
                host_ws.receive_json()
                start_game(client, host["invite_code"], host["player_token"])

                host_started = receive_until_types(host_ws, {"session_snapshot", "private_state"})
                guest_started = receive_until_types(guest_ws, {"session_snapshot", "private_state"})

                host_cards = host_started["private_state"]["data"]["private_cards"][:3]
                guest_cards = guest_started["private_state"]["data"]["private_cards"][:3]

                host_ws.send_json({"type": "choose_public_cards", "cards": host_cards})
                host_after_choose = receive_until_types(host_ws, {"session_snapshot", "private_state"})
                guest_after_host_choose = receive_until_types(guest_ws, {"session_snapshot"})
                assert (
                    host_after_choose["session_snapshot"]["data"]["game_state"]
                    == "PLAYERS_CHOOSE_PUBLIC_CARDS"
                )
                assert (
                    guest_after_host_choose["session_snapshot"]["data"]["players"][0]["public_cards"]
                    != []
                )

                guest_ws.send_json({"type": "choose_public_cards", "cards": guest_cards})
                guest_after_choose = receive_until_types(guest_ws, {"session_snapshot", "private_state"})
                host_after_guest_choose = receive_until_types(host_ws, {"session_snapshot"})
                assert guest_after_choose["session_snapshot"]["data"]["game_state"] == "DURING_GAME"
                assert host_after_guest_choose["session_snapshot"]["data"]["game_state"] == "DURING_GAME"


def test_snapshot_exposes_high_low_constraint_after_playing_seven():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")

        session = session_manager.get_session(host["invite_code"])
        session.start(host["player_token"])
        game = session.game_manager.game
        game.state = GameState.DURING_GAME
        game.deck = PileOfCards()
        game.play_pile = PileOfCards()
        game.valid_ranks = set(range(2, 15))

        host_player = game.get_player(0)
        guest_player = game.get_player(1)
        host_player.private_cards = SetOfCards([Card(SpecialRank.HIGHLOW, Suit.HEART)])
        host_player.public_cards = SetOfCards()
        guest_player.private_cards = SetOfCards([Card(9, Suit.HEART)])
        guest_player.public_cards = SetOfCards()

        session.apply_action(
            host["player_token"],
            ActionRequest(
                type="play_private_cards",
                cards=[CardModel(rank=SpecialRank.HIGHLOW, suit=Suit.HEART)],
                choice="LOWER",
            ),
        )

        snapshot = session.build_snapshot()
        assert snapshot.current_turn_seat == 1
        assert snapshot.status_message == "7 or lower!"


def test_snapshot_exposes_player_name_when_pile_is_taken():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")

        session = session_manager.get_session(host["invite_code"])
        session.start(host["player_token"])
        game = session.game_manager.game
        game.state = GameState.DURING_GAME
        game.deck = PileOfCards()
        game.play_pile = PileOfCards([Card(9, Suit.HEART), Card(6, Suit.CLOVERS)])
        game.valid_ranks = {10, 11, 12}

        host_player = game.get_player(0)
        host_player.private_cards = SetOfCards([Card(4, Suit.HEART)])
        host_player.public_cards = SetOfCards()

        session.apply_action(
            host["player_token"],
            ActionRequest(type="take_play_pile"),
        )

        snapshot = session.build_snapshot()
        assert snapshot.status_message == "Host took the play pile."


def test_hidden_joker_requires_resolution_and_stays_visible_on_play_pile():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")

        session = session_manager.get_session(host["invite_code"])
        session.start(host["player_token"])
        game = session.game_manager.game
        game.state = GameState.DURING_GAME
        game.deck = PileOfCards()
        game.play_pile = PileOfCards()
        game.valid_ranks = set(range(2, 15))

        host_player = game.get_player(0)
        guest_player = game.get_player(1)
        host_player.private_cards = SetOfCards()
        host_player.public_cards = SetOfCards()
        host_player.hidden_cards = SetOfCards([Card(JOKER_RANK, Suit.JOKER_RED)])
        guest_player.private_cards = SetOfCards([Card(9, Suit.HEART)])
        guest_player.public_cards = SetOfCards()

        session.apply_action(host["player_token"], ActionRequest(type="play_hidden_card"))

        pending_snapshot = session.build_snapshot()
        pending_private_state = session.build_private_state(0)
        assert pending_snapshot.pending_joker_selection is True
        assert pending_snapshot.current_turn_seat == 0
        assert pending_private_state.pending_joker_selection is True
        assert pending_private_state.pending_joker_card.is_joker is True

        session.apply_action(host["player_token"], ActionRequest(type="resolve_joker", joker_rank=8))

        resolved_snapshot = session.build_snapshot()
        assert resolved_snapshot.pending_joker_selection is False
        assert resolved_snapshot.status_message == "Skip!"
        assert resolved_snapshot.play_pile[0].is_joker is True
        assert resolved_snapshot.play_pile[0].effective_rank == 8


def test_alpha_session_allows_queen_after_king_and_orders_valid_ranks():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")

        session = session_manager.get_session(host["invite_code"])
        session.start(host["player_token"])
        game = session.game_manager.game
        game.state = GameState.DURING_GAME
        game.deck = PileOfCards()
        game.play_pile = PileOfCards([Card(13, Suit.HEART)])
        game.valid_ranks = RankEvent(RankType.TOPRANK, 13).get_valid_ranks(set(ALL_RANKS))

        host_player = game.get_player(0)
        guest_player = game.get_player(1)
        host_player.private_cards = SetOfCards([Card(12, Suit.CLOVERS)])
        host_player.public_cards = SetOfCards()
        guest_player.private_cards = SetOfCards([Card(3, Suit.HEART)])
        guest_player.public_cards = SetOfCards()

        session.apply_action(
            host["player_token"],
            ActionRequest(
                type="play_private_cards",
                cards=[CardModel(rank=12, suit=Suit.CLOVERS)],
            ),
        )

        snapshot = session.build_snapshot()
        assert snapshot.play_pile[0].rank == 12
        assert snapshot.current_valid_ranks == [2, 5, 10, 12, 14]


def test_alpha_session_rejects_king_after_queen():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")

        session = session_manager.get_session(host["invite_code"])
        session.start(host["player_token"])
        game = session.game_manager.game
        game.state = GameState.DURING_GAME
        game.deck = PileOfCards()
        game.play_pile = PileOfCards([Card(12, Suit.HEART)])
        game.valid_ranks = RankEvent(RankType.TOPRANK, 12).get_valid_ranks(set(ALL_RANKS))

        host_player = game.get_player(0)
        guest_player = game.get_player(1)
        host_player.private_cards = SetOfCards([Card(13, Suit.CLOVERS)])
        host_player.public_cards = SetOfCards()
        guest_player.private_cards = SetOfCards([Card(3, Suit.HEART)])
        guest_player.public_cards = SetOfCards()

        with pytest.raises(CardsNotEligibleOnPlayPileError):
            session.apply_action(
                host["player_token"],
                ActionRequest(
                    type="play_private_cards",
                    cards=[CardModel(rank=13, suit=Suit.CLOVERS)],
                ),
            )
