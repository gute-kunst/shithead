import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from pyshithead import GAME_ID
from pyshithead.main import app, game_tables_manager

from .models_game.conftest import *


@pytest.fixture
def client():
    with TestClient(app) as websocket_client:
        yield websocket_client


@pytest.fixture
def ws_before_joined(client):
    with client.websocket_connect(f"/game/{GAME_ID}") as a:
        with client.websocket_connect(f"/game/{GAME_ID}") as b:
            yield (a, b)


@pytest.fixture
def ws_on_joined(ws_before_joined):
    (a, b) = ws_before_joined
    a.receive_json()
    a.receive_json()
    a.receive_json()
    b.receive_json()
    b.receive_json()
    yield (a, b)


@pytest.fixture
def ws_on_chosen_cards(ws_on_joined):
    (a, b) = ws_on_joined
    a.send_json(json.dumps({"type": "start_game"}))
    a.receive_json()
    a.receive_json()
    a.receive_json()
    b.receive_json()
    b.receive_json()
    b.receive_json()
    private_cards_a = list(
        game_tables_manager.game_tables[0].game_manager.game.get_player(0).private_cards
    )
    a.send_json(
        json.dumps(
            {
                "type": "choose_public_cards",
                "player_id": 0,
                "cards": [vars(card) for card in private_cards_a[:3]],
            }
        )
    )
    yield (a, b)


@pytest.fixture
def ws_on_first_play_request(ws_on_chosen_cards):
    (a, b) = ws_on_chosen_cards
    a.receive_json()
    a.receive_json()
    b.receive_json()
    private_cards_b = list(
        game_tables_manager.game_tables[0].game_manager.game.get_player(1).private_cards
    )
    b.send_json(
        json.dumps(
            {
                "type": "choose_public_cards",
                "player_id": 1,
                "cards": [vars(card) for card in private_cards_b[:3]],
            }
        )
    )
    b.receive_json()
    b.receive_json()
    a.receive_json()
    yield (a, b)


def test_join_adds_client(client: TestClient):
    with client.websocket_connect(f"/game/{GAME_ID}") as websocket:
        data = websocket.receive_json()
        data_broadcast = websocket.receive_json()
        assert "player_id" in data
        nbr_clients = asyncio.run(
            game_tables_manager.get_game_table_by_id(GAME_ID)
        ).client_manager.nbr_of_clients()
        assert data_broadcast == "A new player joined #c: 1"
        assert nbr_clients == 1
        assert (
            asyncio.run(game_tables_manager.get_game_table_by_id(GAME_ID))
            .client_manager.clients[0]
            .id_
            == data["player_id"]
        )


def test_join_two_clients(ws_before_joined):
    nbr_clients = asyncio.run(
        game_tables_manager.get_game_table_by_id(GAME_ID)
    ).client_manager.nbr_of_clients()
    assert nbr_clients == 2


def test_join_two_clients_server_response(ws_before_joined):
    (a, b) = ws_before_joined
    assert {"player_id": 0} == a.receive_json()
    assert "A new player joined #c: 1" == a.receive_json()
    assert {"player_id": 1} == b.receive_json()
    assert "A new player joined #c: 2" == a.receive_json()
    assert "A new player joined #c: 2" == b.receive_json()


def test_start_game(ws_on_joined):
    (a, b) = ws_on_joined
    a.send_json(json.dumps(dict({"type": "start_game"})))
    # RULES
    a_rules = a.receive_json()
    assert "rules" in a_rules.values()
    b_rules = b.receive_json()
    assert "rules" in b_rules.values()
    assert a_rules == b_rules
    # PUBLIC INFO
    a_pub_info = a.receive_json()
    assert "public_info" in a_pub_info.values()
    b_pub_info = b.receive_json()
    assert "public_info" in b_pub_info.values()
    assert a_pub_info == b_pub_info
    # PRIVATE INFO
    a_private_info = a.receive_json()
    assert "private_info" in a_private_info.values()
    b_private_info = b.receive_json()
    assert "private_info" in b_private_info.values()
    assert a_private_info != b_private_info


def test_choose_cards(ws_on_chosen_cards):
    (a, b) = ws_on_chosen_cards
    a_pub_info = a.receive_json()
    a_private_info = a.receive_json()
    assert len(a_private_info["data"]["private_cards"]) == 3
    assert len(a_pub_info["data"]["player_public_info"][0]["public_cards"]) == 3
    b_pub_info = b.receive_json()
    assert a_pub_info == b_pub_info
    assert a_pub_info["data"]["game_state"] == GameState.PLAYERS_CHOOSE_PUBLIC_CARDS
    private_cards_b = list(
        game_tables_manager.game_tables[0].game_manager.game.get_player(1).private_cards
    )
    b.send_json(
        json.dumps(
            {
                "type": "choose_public_cards",
                "player_id": 1,
                "cards": [vars(card) for card in private_cards_b[:3]],
            }
        )
    )
    b_pub_info_2 = b.receive_json()
    b_private_info_2 = b.receive_json()
    a_pub_info_2 = a.receive_json()
    assert a_pub_info_2["data"]["game_state"] == GameState.DURING_GAME
    assert b_pub_info_2 == a_pub_info_2


def test_first_play_request(ws_on_first_play_request):
    (a, b) = ws_on_first_play_request
    private_cards_a = list(
        game_tables_manager.game_tables[0].game_manager.game.get_player(0).private_cards
    )
    a.send_json(
        json.dumps(
            {
                "type": "private_cards",
                "player_id": 0,
                "cards": [vars(private_cards_a[0])],
                "choice": "",  # TODO request fails if private card is high/low
            }  # TODO-2 : test doesnt fail if exception is raised
        )
    )
    b_pub_info = b.receive_json()
    assert b_pub_info["data"]["currents_turn"] == 1
    a_pub_info = a.receive_json()
    a_private_info = a.receive_json()
    assert a_private_info["data"]["private_cards"] != [vars(card) for card in private_cards_a]
    assert True


def test_rest_hello_world(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}


def test_websocket_hello_world(client: TestClient):
    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_json()
        assert data == {"msg": "Hello WebSocket"}
