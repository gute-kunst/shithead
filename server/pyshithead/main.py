"""
start server with
uvicorn main:app --reload
"""

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()
import logging

from pyshithead.models.game import Game, Player
from pyshithead.models.web import Client, GameManager, GameTable

logger = logging.getLogger("websockets")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

manager = GameManager()


@app.get("/")
async def read_main():
    return {"msg": "Hello World"}


@app.websocket("/game/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: int):
    game_table: GameTable = await manager.get_game_table_by_id(game_id)
    client: Client = await game_table.connect(websocket)
    await game_table.send_to_client(client.to_dict(), client.connection)

    try:
        while True:
            data = await websocket.receive_json()
            print(data)
            if data["type"] == "START":
                game_table.game = Game.initialize(
                    [Player(client.client_data.id_) for client in game_table.clients]
                )
                print("SHOULD DO BROADCAST")
                await game_table.broadcast(
                    dict({"type": "started", "game_state": int(game_table.game.state)})
                )

    except WebSocketDisconnect:
        game_table.disconnect(websocket)
        await game_table.broadcast(f"Client left in Game #{game_id}")


@app.websocket("/ws")
async def websocket(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"msg": "Hello WebSocket"})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
