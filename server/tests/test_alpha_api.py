import asyncio
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pyshithead.main import app, create_app, session_manager
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
from pyshithead.models.game.errors import CardsNotEligibleOnPlayPileError
from pyshithead.models.session import GameSessionManager, SQLiteSessionStore
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


def update_game_settings(client: TestClient, invite_code: str, player_token: str, **settings):
    payload = {"player_token": player_token, **settings}
    return client.post(f"/api/games/{invite_code}/settings", json=payload)


def kick_player(client: TestClient, invite_code: str, player_token: str, seat: int):
    return client.post(
        f"/api/games/{invite_code}/players/{seat}/kick",
        json={"player_token": player_token},
    )


def private_card_signature(cards):
    return [
        (
            card["rank"] if isinstance(card, dict) else card.rank,
            card["suit"] if isinstance(card, dict) else card.suit,
            card.get("effective_rank")
            if isinstance(card, dict)
            else getattr(card, "effective_rank", None),
        )
        for card in cards
    ]


def test_create_and_join_alpha_lobby():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        root = client.get("/")
        assert root.status_code == 200
        assert 'id="app" class="app-root"' in root.text
        assert "/static/app.js" in root.text

        health = client.get("/healthz")
        assert health.status_code == 200
        assert health.json() == {"ok": True}

        host = create_game(client, "Host")
        invite_code = host["invite_code"]
        assert host["seat"] == 0
        assert host["snapshot"]["status"] == "LOBBY"
        assert host["snapshot"]["players"][0]["display_name"] == "Host"
        assert host["snapshot"]["rules"]["allow_optional_take_pile"] is False

        guest = join_game(client, invite_code, "Guest")
        assert guest["seat"] == 1
        assert guest["snapshot"]["rules"]["allow_optional_take_pile"] is False

        state = client.get(f"/api/games/{invite_code}")
        assert state.status_code == 200
        snapshot = state.json()["data"]
        assert snapshot["status"] == "LOBBY"
        assert [player["display_name"] for player in snapshot["players"]] == ["Host", "Guest"]
        assert snapshot["rules"]["allow_optional_take_pile"] is False
        assert [preset["key"] for preset in snapshot["shoutout_presets"]] == [
            "hahaha",
            "great-move",
            "wtf",
            "shit",
            "nice",
            "oof",
        ]


def test_lobby_shoutout_broadcasts_live_event_to_connected_players():
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
                host_join_notice = host_ws.receive_json()
                assert host_join_notice["type"] == "session_snapshot"
                assert host_join_notice["data"]["players"][1]["is_connected"] is True

                host_ws.send_json({"type": "send_shoutout", "shoutout_key": "hahaha"})

                host_event = host_ws.receive_json()
                guest_event = guest_ws.receive_json()
                assert host_event["type"] == "shoutout"
                assert guest_event["type"] == "shoutout"
                assert isinstance(host_event["data"]["event_id"], str)
                assert host_event["data"]["event_id"] != ""
                assert guest_event["data"]["event_id"] == host_event["data"]["event_id"]
                assert host_event["data"]["seat"] == 0
                assert host_event["data"]["preset"]["key"] == "hahaha"
                assert guest_event["data"]["preset"]["label"] == "HAHAHA"


def test_shoutout_cooldown_blocks_rapid_repeats(monkeypatch):
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        session = session_manager.get_session(host["invite_code"])
        fixed_now = datetime(2026, 4, 3, 12, 0, 0, tzinfo=timezone.utc)
        monkeypatch.setattr("pyshithead.models.session.manager._utc_now", lambda: fixed_now)

        first_event = session.apply_action(
            host["player_token"],
            ActionRequest(type="send_shoutout", shoutout_key="nice"),
        )
        assert first_event is not None
        assert first_event.data.event_id
        assert first_event.data.preset.key == "nice"
        assert session.get_player_by_seat(0).last_shoutout_at == fixed_now
        assert session.build_private_state(0).shoutout_next_available_at == fixed_now + timedelta(
            seconds=4
        )

        with pytest.raises(ValueError, match="Please wait before sending another shoutout."):
            session.apply_action(
                host["player_token"],
                ActionRequest(type="send_shoutout", shoutout_key="oof"),
            )


def test_build_private_state_includes_shoutout_cooldown_for_lobby_player(monkeypatch):
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        session = session_manager.get_session(host["invite_code"])
        fixed_now = datetime(2026, 4, 3, 12, 0, 0, tzinfo=timezone.utc)
        monkeypatch.setattr("pyshithead.models.session.manager._utc_now", lambda: fixed_now)

        player = session.get_player_by_seat(0)
        player.last_shoutout_at = fixed_now - timedelta(seconds=1)
        active_private_state = session.build_private_state(0)
        assert active_private_state.shoutout_next_available_at == fixed_now + timedelta(seconds=3)

        player.last_shoutout_at = fixed_now - timedelta(seconds=5)
        idle_private_state = session.build_private_state(0)
        assert idle_private_state.shoutout_next_available_at is None


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
                guest_messages = receive_until_types(
                    guest_ws, {"session_snapshot", "private_state"}
                )
                assert (
                    guest_messages["session_snapshot"]["data"]["players"][1]["display_name"]
                    == "Guest"
                )

                join_notice = host_ws.receive_json()
                assert join_notice["type"] == "session_snapshot"
                assert join_notice["data"]["players"][1]["is_connected"] is True

                start_payload = start_game(client, host["invite_code"], host["player_token"])
                assert start_payload["data"]["status"] == "IN_GAME"

                host_started = receive_until_types(host_ws, {"session_snapshot", "private_state"})
                guest_started = receive_until_types(guest_ws, {"session_snapshot", "private_state"})
                assert (
                    host_started["session_snapshot"]["data"]["game_state"]
                    == "PLAYERS_CHOOSE_PUBLIC_CARDS"
                )
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


def test_snapshot_exposes_disconnect_metadata_for_setup_player():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")

        session = session_manager.get_session(host["invite_code"])
        session.start(host["player_token"])
        session.get_player_by_seat(1).connected = False
        session._sync_disconnect_policies()

        snapshot = session.build_snapshot()
        guest = snapshot.players[1]
        assert guest.is_connected is False
        assert guest.last_seen_at
        assert guest.disconnect_deadline_at is not None
        assert guest.disconnect_action == "AUTO_REMOVE_SETUP"


def test_host_can_update_optional_take_pile_setting_in_lobby():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        guest = join_game(client, host["invite_code"], "Guest")

        response = update_game_settings(
            client,
            host["invite_code"],
            host["player_token"],
            allow_optional_take_pile=True,
        )

        assert response.status_code == 200
        assert response.json()["data"]["rules"]["allow_optional_take_pile"] is True

        snapshot = client.get(f"/api/games/{host['invite_code']}").json()["data"]
        assert snapshot["rules"]["allow_optional_take_pile"] is True
        assert guest["snapshot"]["rules"]["allow_optional_take_pile"] is False


def test_non_host_cannot_update_optional_take_pile_setting():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        guest = join_game(client, host["invite_code"], "Guest")

        response = update_game_settings(
            client,
            host["invite_code"],
            guest["player_token"],
            allow_optional_take_pile=True,
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Only the host can change lobby settings."


def test_optional_take_pile_setting_cannot_change_after_start():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")
        start_game(client, host["invite_code"], host["player_token"])

        response = update_game_settings(
            client,
            host["invite_code"],
            host["player_token"],
            allow_optional_take_pile=True,
        )

        assert response.status_code == 400
        assert (
            response.json()["detail"]
            == "Lobby settings can only be changed before the game starts."
        )


def test_fresh_started_game_has_empty_play_pile_during_public_card_selection():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")

        started = start_game(client, host["invite_code"], host["player_token"])

        assert started["data"]["status"] == "IN_GAME"
        assert started["data"]["game_state"] == "PLAYERS_CHOOSE_PUBLIC_CARDS"
        assert started["data"]["play_pile"] == []


def test_host_can_kick_offline_player_from_lobby():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        guest = join_game(client, host["invite_code"], "Guest")

        session = session_manager.get_session(host["invite_code"])
        session._handle_player_disconnect(session.get_player_by_seat(1))

        response = kick_player(client, host["invite_code"], host["player_token"], 1)

        assert response.status_code == 200
        snapshot = response.json()["data"]
        assert [player["display_name"] for player in snapshot["players"]] == ["Host"]

        restored = restore_session(client, host["invite_code"], guest["player_token"])
        assert restored.status_code == 401
        assert restored.json() == {"detail": "Unknown player token."}


def test_host_cannot_kick_connected_player_or_self_and_non_host_cannot_kick():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        guest = join_game(client, host["invite_code"], "Guest")
        session = session_manager.get_session(host["invite_code"])
        session.get_player_by_seat(1).connected = True

        connected_response = kick_player(client, host["invite_code"], host["player_token"], 1)
        assert connected_response.status_code == 400
        assert connected_response.json()["detail"] == "Only offline players can be removed."

        self_response = kick_player(client, host["invite_code"], host["player_token"], 0)
        assert self_response.status_code == 400
        assert self_response.json()["detail"] == "The host cannot remove themselves."

        non_host_response = kick_player(client, host["invite_code"], guest["player_token"], 0)
        assert non_host_response.status_code == 400
        assert non_host_response.json()["detail"] == "Only the host can remove players."


def test_host_can_kick_offline_current_player_during_game():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")
        join_game(client, host["invite_code"], "Third")

        session = session_manager.get_session(host["invite_code"])
        session.start(host["player_token"])
        game = session.game_manager.game
        game.state = GameState.DURING_GAME
        game.active_players.next()
        session.get_player_by_seat(0).connected = True
        session.get_player_by_seat(1).connected = False
        session.get_player_by_seat(2).connected = True

        response = kick_player(client, host["invite_code"], host["player_token"], 1)

        assert response.status_code == 200
        payload = response.json()["data"]
        assert [player["seat"] for player in payload["players"]] == [0, 2]
        assert payload["current_turn_seat"] == 2
        assert "removed while offline" in payload["status_message"]


def test_optional_take_pile_rule_allows_taking_with_playable_card():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")

        session = session_manager.get_session(host["invite_code"])
        session.update_settings(host["player_token"], allow_optional_take_pile=True)
        session.start(host["player_token"])

        game = session.game_manager.game
        game.state = GameState.DURING_GAME
        game.play_pile = PileOfCards([Card(9, Suit.HEART)])
        game.valid_ranks = {9}
        host_player = game.get_player(0)
        host_player.private_cards = SetOfCards([Card(9, Suit.CLOVERS)])

        session.apply_action(host["player_token"], ActionRequest(type="take_play_pile"))

        assert game.play_pile.is_empty()
        assert len(host_player.private_cards) == 2
        assert session.last_status_message == "Host took the play pile."


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


def test_manager_reaps_idle_lobby_session():
    session_manager.sessions.clear()
    session = session_manager.create_session("Host")
    session.last_activity_at = (
        datetime.now(timezone.utc) - session.LOBBY_REAP_AFTER - timedelta(seconds=1)
    )

    with pytest.raises(ValueError, match="Game not found."):
        session_manager.get_session(session.invite_code)


def test_manager_reaps_idle_started_session_and_cancels_disconnect_tasks():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")

        session = session_manager.get_session(host["invite_code"])
        session.start(host["player_token"])

        async def scenario():
            sleeper = asyncio.create_task(asyncio.sleep(60))
            session.disconnect_timeout_tasks[0] = sleeper
            session.last_activity_at = (
                datetime.now(timezone.utc) - session.ACTIVE_REAP_AFTER - timedelta(seconds=1)
            )

            with pytest.raises(ValueError, match="Game not found."):
                session_manager.get_session(host["invite_code"])

            await asyncio.sleep(0)
            assert sleeper.cancelled()

        asyncio.run(scenario())


def test_restore_returns_not_found_for_reaped_session():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        session = session_manager.get_session(host["invite_code"])
        session.last_activity_at = (
            datetime.now(timezone.utc) - session.LOBBY_REAP_AFTER - timedelta(seconds=1)
        )

        restored = restore_session(client, host["invite_code"], host["player_token"])

        assert restored.status_code == 404
        assert restored.json() == {"detail": "Game not found."}


def test_persisted_session_survives_manager_restart():
    file_descriptor, raw_path = tempfile.mkstemp(suffix="-restart-state.db")
    try:
        os.close(file_descriptor)
    except OSError:
        pass
    Path(raw_path).unlink(missing_ok=True)
    database_url = f"sqlite:///{Path(raw_path).as_posix()}"
    first_manager = None
    second_manager = None
    try:
        first_manager = GameSessionManager(store=SQLiteSessionStore(database_url))
        first_app = create_app(session_manager=first_manager)

        with TestClient(first_app, base_url="http://localhost") as client:
            host = create_game(client, "Host")
            guest = join_game(client, host["invite_code"], "Guest")

            update_response = update_game_settings(
                client,
                host["invite_code"],
                host["player_token"],
                allow_optional_take_pile=True,
            )
            assert update_response.status_code == 200

            started = start_game(client, host["invite_code"], host["player_token"])
            assert started["data"]["status"] == "IN_GAME"

        second_manager = GameSessionManager(store=SQLiteSessionStore(database_url))
        second_app = create_app(session_manager=second_manager)

        with TestClient(second_app, base_url="http://localhost") as client:
            restored = restore_session(client, host["invite_code"], guest["player_token"])

            assert restored.status_code == 200
            payload = restored.json()
            assert payload["snapshot"]["status"] == "IN_GAME"
            assert payload["snapshot"]["game_state"] == "PLAYERS_CHOOSE_PUBLIC_CARDS"
            assert payload["snapshot"]["rules"]["allow_optional_take_pile"] is True
            assert payload["snapshot"]["players"][0]["is_connected"] is False
            assert payload["snapshot"]["players"][1]["is_connected"] is False
            assert payload["snapshot"]["players"][0]["disconnect_action"] == "AUTO_REMOVE_SETUP"
            assert payload["snapshot"]["players"][1]["disconnect_action"] == "AUTO_REMOVE_SETUP"
            assert payload["snapshot"]["players"][0]["disconnect_deadline_at"] is not None
            assert payload["snapshot"]["players"][1]["disconnect_deadline_at"] is not None
            assert len(payload["private_state"]["private_cards"]) == 6
    finally:
        if first_manager is not None:
            first_manager.sessions.clear()
        if second_manager is not None:
            second_manager.sessions.clear()
        try:
            Path(raw_path).unlink(missing_ok=True)
        except PermissionError:
            pass


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
                host_after_choose = receive_until_types(
                    host_ws, {"session_snapshot", "private_state"}
                )
                guest_after_host_choose = receive_until_types(guest_ws, {"session_snapshot"})
                assert (
                    host_after_choose["session_snapshot"]["data"]["game_state"]
                    == "PLAYERS_CHOOSE_PUBLIC_CARDS"
                )
                assert (
                    guest_after_host_choose["session_snapshot"]["data"]["players"][0][
                        "public_cards"
                    ]
                    != []
                )

                guest_ws.send_json({"type": "choose_public_cards", "cards": guest_cards})
                guest_after_choose = receive_until_types(
                    guest_ws, {"session_snapshot", "private_state"}
                )
                host_after_guest_choose = receive_until_types(host_ws, {"session_snapshot"})
                assert guest_after_choose["session_snapshot"]["data"]["game_state"] == "DURING_GAME"
                assert (
                    host_after_guest_choose["session_snapshot"]["data"]["game_state"]
                    == "DURING_GAME"
                )


def test_disconnect_timeout_skips_current_player_and_clears_pending_joker():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")
        join_game(client, host["invite_code"], "Third")

        session = session_manager.get_session(host["invite_code"])
        session.start(host["player_token"])
        game = session.game_manager.game
        game.state = GameState.DURING_GAME
        game.deck = PileOfCards()
        game.play_pile = PileOfCards([Card(JOKER_RANK, Suit.JOKER_RED)])
        game.get_player(0).private_cards = SetOfCards()
        game.get_player(0).public_cards = SetOfCards()
        game.get_player(0).hidden_cards = SetOfCards([Card(6, Suit.HEART)])
        session.pending_joker_seat = 0
        session.pending_joker_card = Card(JOKER_RANK, Suit.JOKER_RED)

        session.get_player_by_seat(0).connected = False
        session.get_player_by_seat(1).connected = True
        session.get_player_by_seat(2).connected = True

        asyncio.run(session._apply_disconnect_timeout(0))

        snapshot = session.build_snapshot()
        assert snapshot.current_turn_seat == 1
        assert (
            snapshot.status_message
            == "Host disconnected after revealing joker and took the play pile."
        )
        assert snapshot.pending_joker_selection is False
        assert session.pending_joker_seat is None
        assert session.pending_joker_card is None
        assert snapshot.play_pile == []
        assert len(game.get_player(0).private_cards) == 1
        assert {player.seat for player in session.players} == {0, 1, 2}


def test_disconnect_timeout_does_not_skip_non_current_player():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")
        join_game(client, host["invite_code"], "Third")

        session = session_manager.get_session(host["invite_code"])
        session.start(host["player_token"])
        game = session.game_manager.game
        game.state = GameState.DURING_GAME
        game.deck = PileOfCards()
        game.play_pile = PileOfCards()

        session.get_player_by_seat(0).connected = True
        session.get_player_by_seat(1).connected = False
        session.get_player_by_seat(2).connected = True

        asyncio.run(session._apply_disconnect_timeout(1))

        snapshot = session.build_snapshot()
        assert snapshot.current_turn_seat == 0
        assert snapshot.status_message is None
        assert session.get_player_by_seat(1).connected is False


def test_disconnect_timeout_noops_if_player_reconnected_before_expiry():
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

        session.get_player_by_seat(0).connected = True
        session.get_player_by_seat(1).connected = True

        asyncio.run(session._apply_disconnect_timeout(0))

        snapshot = session.build_snapshot()
        assert snapshot.current_turn_seat == 0
        assert snapshot.status_message is None


def test_disconnect_timeout_removes_setup_player_and_starts_game_with_remaining_players():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")
        third = join_game(client, host["invite_code"], "Third")

        session = session_manager.get_session(host["invite_code"])
        session.start(host["player_token"])
        game = session.game_manager.game
        game.get_player(0).public_cards = SetOfCards()
        game.get_player(2).public_cards = SetOfCards()

        session.get_player_by_seat(0).connected = True
        session.get_player_by_seat(1).connected = False
        session.get_player_by_seat(2).connected = True

        asyncio.run(session._apply_disconnect_timeout(1))

        snapshot = session.build_snapshot()
        assert snapshot.game_state == "DURING_GAME"
        assert (
            snapshot.status_message == "Guest disconnected and was removed before the game began."
        )
        assert [player.seat for player in snapshot.players] == [0, 2]
        assert third["player_token"] in {player.token for player in session.players}


def test_disconnect_timeout_removes_setup_player_and_returns_to_lobby_if_too_few_players():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        guest = join_game(client, host["invite_code"], "Guest")

        session = session_manager.get_session(host["invite_code"])
        session.start(host["player_token"])
        session.get_player_by_seat(0).connected = True
        session.get_player_by_seat(1).connected = False

        asyncio.run(session._apply_disconnect_timeout(1))

        snapshot = session.build_snapshot()
        assert session.game_manager is None
        assert snapshot.status == "LOBBY"
        assert (
            snapshot.status_message == "Guest disconnected and was removed before the game began."
        )
        assert [player.seat for player in snapshot.players] == [0]

        restored = restore_session(client, host["invite_code"], guest["player_token"])
        assert restored.status_code == 401
        assert restored.json() == {"detail": "Unknown player token."}


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
        assert pending_snapshot.play_pile[0].is_joker is True
        assert pending_private_state.pending_joker_selection is True
        assert pending_private_state.pending_joker_card.is_joker is True

        session.apply_action(
            host["player_token"], ActionRequest(type="resolve_joker", joker_rank=8)
        )

        resolved_snapshot = session.build_snapshot()
        assert resolved_snapshot.pending_joker_selection is False
        assert resolved_snapshot.status_message == "Skip!"
        assert resolved_snapshot.play_pile[0].is_joker is True
        assert resolved_snapshot.play_pile[0].effective_rank == 8


def test_hidden_seven_requires_high_low_choice_after_being_revealed():
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
        host_player.hidden_cards = SetOfCards([Card(SpecialRank.HIGHLOW, Suit.HEART)])
        guest_player.private_cards = SetOfCards([Card(9, Suit.HEART)])
        guest_player.public_cards = SetOfCards()

        session.apply_action(host["player_token"], ActionRequest(type="play_hidden_card"))

        pending_snapshot = session.build_snapshot()
        pending_private_state = session.build_private_state(0)
        assert pending_snapshot.current_turn_seat == 0
        assert pending_snapshot.play_pile[0].rank == SpecialRank.HIGHLOW
        assert pending_private_state.pending_joker_selection is True

        session.apply_action(
            host["player_token"],
            ActionRequest(type="resolve_joker", choice="LOWER"),
        )

        resolved_snapshot = session.build_snapshot()
        assert resolved_snapshot.current_turn_seat == 1
        assert resolved_snapshot.status_message == "7 or lower!"


def test_revealed_seven_accepts_nullable_joker_rank_when_resolved():
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
        host_player.hidden_cards = SetOfCards([Card(SpecialRank.HIGHLOW, Suit.HEART)])
        guest_player.private_cards = SetOfCards([Card(9, Suit.HEART)])
        guest_player.public_cards = SetOfCards()

        session.apply_action(host["player_token"], ActionRequest(type="play_hidden_card"))

        pending_snapshot = session.build_snapshot()
        pending_private_state = session.build_private_state(0)
        assert pending_snapshot.current_turn_seat == 0
        assert pending_snapshot.play_pile[0].rank == SpecialRank.HIGHLOW
        assert pending_private_state.pending_joker_selection is True

        session.apply_action(
            host["player_token"],
            ActionRequest(type="resolve_joker", choice="LOWER", joker_rank=None),
        )

        resolved_snapshot = session.build_snapshot()
        assert resolved_snapshot.current_turn_seat == 1
        assert resolved_snapshot.status_message == "7 or lower!"


def test_unplayable_hidden_seven_requires_taking_the_pile_not_high_low_choice():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")

        session = session_manager.get_session(host["invite_code"])
        session.start(host["player_token"])
        game = session.game_manager.game
        game.state = GameState.DURING_GAME
        game.deck = PileOfCards()
        game.play_pile = PileOfCards([Card(9, Suit.HEART)])
        game.valid_ranks = {10, 11, 12}

        host_player = game.get_player(0)
        guest_player = game.get_player(1)
        host_player.private_cards = SetOfCards()
        host_player.public_cards = SetOfCards()
        host_player.hidden_cards = SetOfCards([Card(SpecialRank.HIGHLOW, Suit.HEART)])
        guest_player.private_cards = SetOfCards([Card(12, Suit.HEART)])
        guest_player.public_cards = SetOfCards()

        session.apply_action(host["player_token"], ActionRequest(type="play_hidden_card"))

        pending_snapshot = session.build_snapshot()
        pending_private_state = session.build_private_state(0)
        assert pending_snapshot.current_turn_seat == 0
        assert pending_snapshot.play_pile[0].rank == SpecialRank.HIGHLOW
        assert pending_snapshot.pending_joker_selection is False
        assert pending_private_state.pending_joker_selection is False
        assert pending_private_state.pending_hidden_take is True
        assert pending_snapshot.status_message == "Host revealed 7 and must take the pile."

        session.apply_action(host["player_token"], ActionRequest(type="take_play_pile"))

        resolved_snapshot = session.build_snapshot()
        resolved_private_state = session.build_private_state(0)
        assert resolved_snapshot.current_turn_seat == 1
        assert resolved_snapshot.play_pile == []
        assert resolved_snapshot.status_message == "Host took the play pile."
        assert resolved_private_state.pending_hidden_take is False
        assert any(
            card.rank == SpecialRank.HIGHLOW for card in resolved_private_state.private_cards
        )


def test_unplayable_hidden_card_stays_visible_and_requires_taking_the_pile():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")

        session = session_manager.get_session(host["invite_code"])
        session.start(host["player_token"])
        game = session.game_manager.game
        game.state = GameState.DURING_GAME
        game.deck = PileOfCards()
        game.play_pile = PileOfCards([Card(9, Suit.HEART)])
        game.valid_ranks = {10, 11, 12}

        host_player = game.get_player(0)
        guest_player = game.get_player(1)
        host_player.private_cards = SetOfCards()
        host_player.public_cards = SetOfCards()
        host_player.hidden_cards = SetOfCards([Card(4, Suit.CLOVERS)])
        guest_player.private_cards = SetOfCards([Card(12, Suit.HEART)])
        guest_player.public_cards = SetOfCards()

        session.apply_action(host["player_token"], ActionRequest(type="play_hidden_card"))

        pending_snapshot = session.build_snapshot()
        pending_private_state = session.build_private_state(0)
        assert pending_snapshot.current_turn_seat == 0
        assert pending_snapshot.play_pile[0].rank == 4
        assert pending_private_state.pending_hidden_take is True
        assert pending_snapshot.status_message == "Host revealed 4 and must take the pile."

        session.apply_action(host["player_token"], ActionRequest(type="take_play_pile"))

        resolved_snapshot = session.build_snapshot()
        resolved_private_state = session.build_private_state(0)
        assert resolved_snapshot.current_turn_seat == 1
        assert resolved_snapshot.play_pile == []
        assert resolved_snapshot.status_message == "Host took the play pile."
        assert resolved_private_state.pending_hidden_take is False
        assert any(card.rank == 4 for card in resolved_private_state.private_cards)


def test_disconnect_timeout_clears_pending_hidden_take_by_taking_the_pile():
    session_manager.sessions.clear()
    with TestClient(app, base_url="http://localhost") as client:
        host = create_game(client, "Host")
        join_game(client, host["invite_code"], "Guest")

        session = session_manager.get_session(host["invite_code"])
        session.start(host["player_token"])
        game = session.game_manager.game
        game.state = GameState.DURING_GAME
        game.deck = PileOfCards()
        game.play_pile = PileOfCards([Card(9, Suit.HEART), Card(4, Suit.CLOVERS)])
        game.valid_ranks = {10, 11, 12}
        session.pending_hidden_take_seat = 0

        host_player = game.get_player(0)
        guest_player = game.get_player(1)
        host_player.private_cards = SetOfCards()
        host_player.public_cards = SetOfCards()
        host_player.hidden_cards = SetOfCards([Card(6, Suit.HEART)])
        guest_player.private_cards = SetOfCards([Card(12, Suit.HEART)])
        guest_player.public_cards = SetOfCards()

        session.get_player_by_seat(0).connected = False
        session.get_player_by_seat(1).connected = True

        asyncio.run(session._apply_disconnect_timeout(0))

        snapshot = session.build_snapshot()
        private_state = session.build_private_state(0)
        assert snapshot.current_turn_seat == 1
        assert snapshot.play_pile == []
        assert (
            snapshot.status_message
            == "Host disconnected after revealing a hidden card and took the play pile."
        )
        assert private_state.pending_hidden_take is False


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
