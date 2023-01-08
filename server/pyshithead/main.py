"""
start server with
uvicorn main:app --reload
"""

import json

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()
import logging

from pyshithead.models.web import GameTable, GameTablesManager

logger = logging.getLogger("websockets")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

game_tables_manager = GameTablesManager()


@app.get("/")
async def read_main():
    return {"msg": "Hello World"}


@app.websocket("/game/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: int):
    game_table: GameTable = await game_tables_manager.get_game_table_by_id(game_id)
    await game_table.add_client(websocket)
    try:
        while True:
            req = await websocket.receive_json()
            data = json.loads(req)
            if data["type"] == "start_game":
                await game_table.start_game()
            elif (
                data["type"] == "private_cards"
                or data["type"] == "take_play_pile"
                or data["type"] == "hidden_card"
                or data["type"] == "choose_public_cards"
            ):
                await game_table.game_request(data)
    except WebSocketDisconnect:
        game_table.client_manager.disconnect(websocket)
        await game_table.client_manager.broadcast(f"Client left in Game #{game_id}")


@app.websocket("/ws")
async def websocket(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"msg": "Hello WebSocket"})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
