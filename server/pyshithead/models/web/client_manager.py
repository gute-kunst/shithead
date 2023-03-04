from fastapi import WebSocket

from pyshithead.models.common import request_models
from pyshithead.models.web import Client


class ClientManager:
    def __init__(self):
        self.clients: list[Client] = []

    def get_connections(self):
        return [client.connection for client in self.clients]

    async def connect(self, websocket: WebSocket) -> Client:
        await websocket.accept()
        client = Client(connection=websocket, id=len(self.clients))
        self.clients.append(client)
        print(f"number of clients: {len(self.clients)}")
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

    async def broadcast_log(self, message: str):
        for connection in self.get_connections():
            await connection.send_json(request_models.Log(message=message).dict())

    def nbr_of_clients(self):
        return len(self.clients)
