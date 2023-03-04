import random

from fastapi import WebSocket

from pyshithead.models.common import GameManager, request_models
from pyshithead.models.game import PyshitheadError
from pyshithead.models.web import ClientManager


class GameTable:
    def __init__(self, game_id=None):
        self.game_manager: GameManager = None
        self.game_id = random.randint(0, 999) if game_id is None else game_id
        self.client_manager: ClientManager = ClientManager()

    async def add_client(self, websocket: WebSocket):
        client = await self.client_manager.connect(websocket)
        await client.send(request_models.ClientModel.from_client(client).dict())
        await self.client_manager.broadcast_log(
            message=f"A new player joined. player-id: {client.id_}"
        )

        await self.client_manager.broadcast(
            request_models.GameTable(
                data=request_models.GameTableData(
                    nbr_of_players=self.client_manager.nbr_of_clients(),
                    clients=[
                        request_models.ClientModel.from_client(client)
                        for client in self.client_manager.clients
                    ],
                )
            ).dict()
        )

    async def start_game(self):
        self.game_manager: GameManager = GameManager(
            player_ids=[client.id_ for client in self.client_manager.clients]
        )
        await self.client_manager.broadcast(self.game_manager.get_rules())
        await self.client_manager.broadcast(self.game_manager.get_public_infos())
        for client in self.client_manager.clients:
            await client.send(self.game_manager.get_private_infos(client.id_))

    async def game_request(self, req: request_models.BaseRequest):
        client = self.client_manager.get_client_by_id(req.player_id)
        try:
            self.game_manager.process_request(req)
            await self.broadcast_game_state()
            print("game_state", self.game_manager.game.state)
            await client.send(self.game_manager.get_private_infos(client.id_))
        except PyshitheadError as err:
            await client.send({"type": "invalid-request", "data": err.message})
            print(f"🔥 Error: {err.message} 👉 Try Again")

    async def broadcast_game_state(self):
        await self.client_manager.broadcast(self.game_manager.get_public_infos())
