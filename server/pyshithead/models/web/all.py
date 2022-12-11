import random
import string
import time
from dataclasses import dataclass, field
from typing import Optional

from fastapi import WebSocket
from pyshithead import GAME_ID, INVITE_LINK
from pyshithead.models.game import Game
from pyshithead.models.web.errors import GameTableNotFoundError


class ClientData:
    def __init__(self):
        # self.secret: str = "".join(
        #     random.choice(string.ascii_uppercase + string.digits) for _ in range(8)
        # )
        self.id_ = random.randint(0, 999)
        self.name: str = "".join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(3)
        )


class Client:
    def __init__(self, connection):
        self.connection: WebSocket = connection
        self.client_data: ClientData = ClientData()

    def to_dict(self):
        return vars(self.client_data)


@dataclass
class GameTable:
    game: Optional[Game]
    game_id: int
    # invite_link: str
    clients: list[Client] = field(default_factory=list)

    def get_connections(self):
        return [client.connection for client in self.clients]

    async def connect(self, websocket: WebSocket) -> Client:
        await websocket.accept()
        client = Client(connection=websocket)
        self.clients.append(client)
        print(f"number of clients: {len(self.clients)}")
        print(client.to_dict())
        return client

    def disconnect(self, websocket: WebSocket):
        for client in self.clients:
            if websocket == client.connection:
                print(f"{client} has left")
                self.clients.remove(client)

    async def send_to_client(self, data: str, websocket: WebSocket):
        await websocket.send_json(data)

    async def broadcast(self, data: str | dict):
        for connection in self.get_connections():
            await connection.send_json(data)


class GameManager:
    def __init__(self):
        # self.active_connections: list[WebSocket] = []
        self.game_tables: list[GameTable] = [GameTable(game=None, game_id=GAME_ID)]

    async def get_game_table_by_id(self, game_id: int) -> GameTable:
        for game in self.game_tables:
            if game.game_id == game_id:
                return game
        raise GameTableNotFoundError(game_id)
