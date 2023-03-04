"""
start server with
uvicorn pyshithead.main:app --reload
"""


import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from pyshithead.models.common import request_models
from pyshithead.models.web import GameTable, GameTablesManager

app = FastAPI()
import logging

logger = logging.getLogger("websockets")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

game_tables_manager = GameTablesManager()


@app.get("/", response_class=HTMLResponse)
async def read_main():
    return """
    <html>
        <body>
            <h1>Shithead Browser game</h1>
        </body>
    </html>
    """
    # return {"msg": "Hello World"}


@app.websocket("/game/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: int):
    game_table: GameTable = await game_tables_manager.get_game_table_by_id(game_id)
    await game_table.add_client(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data["type"] == "start_game":
                await game_table.start_game()
            else:
                request = request_models.request_factory(data)
                await game_table.game_request(request)
    except WebSocketDisconnect:
        game_table.client_manager.disconnect(websocket)
        await game_table.client_manager.broadcast(f"Client left in Game #{game_id}")


@app.websocket("/ws")
async def websocket(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"msg": "Hello WebSocket"})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
