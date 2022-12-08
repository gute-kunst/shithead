"""
start server with
uvicorn main:app --reload
"""
import random
import string
from dataclasses import dataclass, field
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()
import json

from pyshithead import Game


class ClientData:
    def __init__(self):
        self.secret: str = "".join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(8)
        )
        self.name: str = "".join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(3)
        )


class Client:
    def __init__(self, connection):
        self.connection: WebSocket
        self.client_data: ClientData = ClientData()

    def to_dict(self):
        return vars(self.client_data)


@dataclass
class WebGame:
    game: Optional[Game]
    game_id: int
    # invite_link: str
    clients: list[Client] = field(default_factory=list)


GAME_ID = 1
INVITE_LINK = f"ws://localhost:8000/join/{GAME_ID}"


class WebGameList:
    def __init__(self, game_list: list[WebGame] = []):
        self.game_list: list[WebGame] = game_list

    def __iter__(self):
        return iter(self.game_list)

    def __getitem__(self, game_id):
        for game in self:
            if game.game_id == game_id:
                return game


class ConnectionManager:
    def __init__(self):
        # self.active_connections: list[WebSocket] = []
        self.games: WebGameList = WebGameList([WebGame(game=None, game_id=GAME_ID)])

    async def connect(self, websocket: WebSocket, game_id=int):
        await websocket.accept()
        client = Client(connection=websocket)
        self.games[game_id].clients.append(client)
        print(f"number of clients: {len(self.games[game_id].clients)}")
        # self.active_connections.append(websocket)
        print(client.to_dict())
        return client

    def disconnect(self, websocket: WebSocket):
        pass
        # self.active_connections.remove(websocket)

    async def send_to_client(self, data: str, websocket: WebSocket):
        await websocket.send_json(data)

    async def broadcast(self, data: str):
        for connection in [client.connection for client in self.games[1].clients]:
            await connection.send_json(data)


manager = ConnectionManager()


@app.websocket("/join/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: int):
    client = await manager.connect(websocket, game_id)
    await manager.send_to_client(client.to_dict(), websocket)
    try:
        while True:
            pass
        # if len(manager.games[game_id].clients) == 2:
        #     await manager.broadcast(f"Two Players: The Game can begin")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{game_id} left the chat")
