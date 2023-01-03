import asyncio
import json
import time

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from httpx import AsyncClient

from pyshithead import GAME_ID
from pyshithead.main import app, game_tables_manager


@pytest.fixture
def client():
    with TestClient(app) as websocket_client:
        yield websocket_client


# @pytest.fixture(scope="session")
# def event_loop():
#     loop = asyncio.get_event_loop()
#     yield loop
#     loop.close()


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


def test_join_two_clients(client: TestClient):
    with client.websocket_connect(f"/game/{GAME_ID}"):
        with client.websocket_connect(f"/game/{GAME_ID}"):
            nbr_clients = asyncio.run(
                game_tables_manager.get_game_table_by_id(GAME_ID)
            ).client_manager.nbr_of_clients()
            assert nbr_clients == 2


def test_join_two_clients_server_response(client: TestClient):
    with client.websocket_connect(f"/game/{GAME_ID}") as a:
        a_1 = a.receive_json()
        assert a_1 == {"player_id": 0}
        a_2 = a.receive_json()
        assert a_2 == "A new player joined #c: 1"
        with client.websocket_connect(f"/game/{GAME_ID}") as b:
            b_1 = b.receive_json()
            assert b_1 == {"player_id": 1}
            a_3 = a.receive_json()
            assert a_3 == "A new player joined #c: 2"
            b_2 = b.receive_json()
            assert b_2 == "A new player joined #c: 2"


def test_start_game(client: TestClient):
    with client.websocket_connect(f"/game/{GAME_ID}") as a:
        a_1 = a.receive_json()
        assert a_1 == {"player_id": 0}
        a_2 = a.receive_json()
        assert a_2 == "A new player joined #c: 1"
        with client.websocket_connect(f"/game/{GAME_ID}") as b:
            b_1 = b.receive_json()
            assert b_1 == {"player_id": 1}
            a_3 = a.receive_json()
            assert a_3 == "A new player joined #c: 2"
            b_2 = b.receive_json()
            assert b_2 == "A new player joined #c: 2"
            # START GAME
            a.send_json(json.dumps(dict({"type": "start_game"})))
            # RULES
            a_rules = a.receive_json()
            assert "rules" in a_rules.values()
            b_rules = b.receive_json()
            assert "rules" in b_rules.values()
            # # PUBLIC INFO
            a_pub_info = a.receive_json()
            assert "public_info" in a_pub_info.values()
            b_pub_info = b.receive_json()
            assert "public_info" in b_pub_info.values()


def test_rest_hello_world(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}


def test_websocket_hello_world(client: TestClient):
    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_json()
        assert data == {"msg": "Hello WebSocket"}
