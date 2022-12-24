import random

from fastapi import WebSocket

from pyshithead import GAME_ID
from pyshithead.models.game import GameManager, GameState, PyshitheadError
from pyshithead.models.web.errors import GameTableNotFoundError


class Client:
    def __init__(self, connection):
        self.connection: WebSocket = connection
        self.id_: int = random.randint(0, 999)
        # self.name: str = "".join(
        #     random.choice(string.ascii_uppercase + string.digits) for _ in range(3)
        # )

    async def send(self, data):
        await self.connection.send_json(data)

    def to_dict(self):
        return dict({"player_id": self.id_})


class ClientManager:
    def __init__(self):
        self.clients: list[Client] = []

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
        # TODO Game model doesnt reflect leaving player

    # async def send_to_client(self, data: str, websocket: WebSocket):
    # await websocket.send_json(data)
    def get_client_by_id(self, id):
        for client in self.clients:
            if client.id_ == id:
                return client
        # raise ClientNotFoundError # TODO

    async def broadcast(self, data: str | dict):
        for connection in self.get_connections():
            await connection.send_json(data)

    def nbr_of_clients(self):
        return len(self.clients)


class GameTable:
    def __init__(self, game_id=None):
        self.game_manager: GameManager = None
        if game_id is None:
            self.game_id: int = random.randint(0, 999)
        else:
            self.game_id = game_id
        self.client_manager: ClientManager = ClientManager()

    async def add_client(self, websocket: WebSocket):
        client = await self.client_manager.connect(websocket)
        await client.send(client.to_dict())
        await self.client_manager.broadcast("A new player joined")

    def start_game(self):
        self.game_manager = GameManager(
            player_ids=[client.id_ for client in self.client_manager.clients]
        )
        self.client_manager.broadcast(self.game_manager.get_rules())
        self.client_manager.broadcast(self.game_manager.get_public_infos())
        for client in self.client_manager.clients:
            client.send(self.game_manager.get_private_infos(client.id_))

    async def game_request(self, req: dict):
        client = self.client_manager.get_client_by_id(req["player_id"])
        if req["type"] == "choose_public_cards":
            self.game_manager.process_request(req)
            if self.game_manager.game.state == GameState.PLAYERS_CHOOSE_PUBLIC_CARDS:
                pass  # TODO
                print("what to do here?")
            elif self.game_manager.game.state == GameState.DURING_GAME:
                await self.broadcast_game_state()
            else:
                pass  # TODO
                print("what to do here?")

        elif (
            req["type"] == "private_cards"
            or req["type"] == "take_play_pile"
            or req["type"] == "hidden_card"
        ):
            try:
                self.game_manager.process_request(req)
                await self.broadcast_game_state()
                await client.send(self.game_manager.get_private_infos(client.id_))
            except PyshitheadError as err:
                print(f"🔥 Error: {err.message} 👉 Try Again")

    async def broadcast_game_state(self):
        await self.client_manager.broadcast(self.game_manager.get_public_infos())


class GameTablesManager:
    def __init__(self):
        self.game_tables: list[GameTable] = [GameTable(game_id=GAME_ID)]

    async def get_game_table_by_id(self, game_id: int) -> GameTable:
        for game in self.game_tables:
            return game
        raise GameTableNotFoundError(game_id)

    def add_game_table(self):
        raise NotImplementedError
