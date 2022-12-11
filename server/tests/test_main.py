import asyncio

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from pyshithead import GAME_ID
from pyshithead.main import app, manager
from pyshithead.models.web import Client, GameManager, GameTable


def test_websocket():
    client = TestClient(app)
    with client.websocket_connect(f"/game/{GAME_ID}") as websocket:
        data = websocket.receive_json()
        # assert "secret" in data
        assert "name" in data
        nbr_clients = len(asyncio.run(manager.get_game_table_by_id(GAME_ID)).clients)
        assert nbr_clients == 1


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
