import asyncio
import json

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient

from pyshithead import GAME_ID
from pyshithead.main import app, game_tables_manager


def test_join_adds_client():
    client = TestClient(app)
    with client.websocket_connect(f"/game/{GAME_ID}") as websocket:
        data = websocket.receive_json()
        assert "player_id" in data
        nbr_clients = asyncio.run(
            game_tables_manager.get_game_table_by_id(GAME_ID)
        ).client_manager.nbr_of_clients()
        assert nbr_clients == 1
        assert (
            asyncio.run(game_tables_manager.get_game_table_by_id(GAME_ID))
            .client_manager.clients[0]
            .id_
            == data["player_id"]
        )


def test_join_two_clients():
    client = TestClient(app)
    with client.websocket_connect(f"/game/{GAME_ID}"):
        with client.websocket_connect(f"/game/{GAME_ID}"):
            nbr_clients = asyncio.run(
                game_tables_manager.get_game_table_by_id(GAME_ID)
            ).client_manager.nbr_of_clients()
            assert nbr_clients == 2


# def test_start_game():
#     client = TestClient(app)
#     with client.websocket_connect(f"/game/{GAME_ID}") as ws1:
#         with client.websocket_connect(f"/game/{GAME_ID}") as ws2:
#             data = ws1.receive_json()
#             print(data)
#             ws1.send_json(json.dumps(dict({"type": "start_game"})))
#             data2 = ws1.receive_json()
#             assert {"type": "rules"} in data

#             print(data2)
#             print("game started")


def test_rest_hello_world():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}


def test_websocket_hello_world():
    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_json()
        assert data == {"msg": "Hello WebSocket"}
