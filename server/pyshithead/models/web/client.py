import random
from typing import Optional

from fastapi import WebSocket


class Client:
    def __init__(self, connection, id: Optional[int] = None):
        self.connection: WebSocket = connection
        self.id_ = random.randint(0, 999) if id is None else id

    async def send(self, data):
        await self.connection.send_json(data)

    def to_dict(self):
        return dict({"type": "player_id", "player_id": self.id_})
