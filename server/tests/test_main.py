import asyncio
import json

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient

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
        assert data_broadcast == "A new player joined"
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


# @pytest.mark.asyncio
# async def test_start_game(client: TestClient):
#     with client.websocket_connect(f"/game/{GAME_ID}") as ws1:
#         with client.websocket_connect(f"/game/{GAME_ID}") as ws2:
#             data1_ws1 = ws1.receive_json()
#             print(data1_ws1)
#             data1_ws2 = ws2.receive_json()
#             print(data1_ws2)
#             data2_ws1 = ws1.receive_json()
#             print(data2_ws1)
#             data2_ws2 = ws2.receive_json()
#             print(data2_ws2)
#             # assert False
#             ws1.send_json(json.dumps(dict({"type": "start_game"})))
#             data3_ws1 = ws1.receive_json()
#             print(data3_ws1)
#             data3_ws2 = ws2.receive_json()
#             print(data3_ws2)
#             assert {"type": "rules"} in data3_ws1


def test_rest_hello_world(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}


def test_websocket_hello_world(client: TestClient):
    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_json()
        assert data == {"msg": "Hello WebSocket"}
