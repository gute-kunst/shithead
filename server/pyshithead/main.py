"""
start server with
uvicorn pyshithead.main:app --reload
"""

from pathlib import Path
import logging

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from pyshithead.models.game import PyshitheadError
from pyshithead.models.session import (
    ActionRequest,
    CreateGameRequest,
    GameSessionManager,
    JoinGameRequest,
    RestoreSessionRequest,
    SessionAuthResponse,
    SessionSnapshotEvent,
    StartGameRequest,
)

app = FastAPI()

logger = logging.getLogger("websockets")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

session_manager = GameSessionManager()
STATIC_DIR = Path(__file__).resolve().parent / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _http_error(err: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(err))


@app.get("/", response_class=HTMLResponse)
async def read_main():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/healthz")
async def healthcheck():
    return {"ok": True}


@app.post("/api/games", response_model=SessionAuthResponse)
async def create_game(payload: CreateGameRequest):
    try:
        session = session_manager.create_session(payload.display_name)
    except ValueError as err:
        raise _http_error(err) from err
    return session.auth_response(session.get_player_by_token(session.host_token))


@app.post("/api/games/{invite_code}/join", response_model=SessionAuthResponse)
async def join_game(invite_code: str, payload: JoinGameRequest):
    try:
        session = session_manager.get_session(invite_code)
        player = session.join(payload.display_name)
    except ValueError as err:
        raise _http_error(err) from err
    await session.broadcast_snapshot()
    return session.auth_response(player)


@app.post("/api/games/{invite_code}/start", response_model=SessionSnapshotEvent)
async def start_game(invite_code: str, payload: StartGameRequest):
    try:
        session = session_manager.get_session(invite_code)
        session.start(payload.player_token)
    except ValueError as err:
        raise _http_error(err) from err
    await session.broadcast_full_state()
    return SessionSnapshotEvent(data=session.build_snapshot())


@app.post("/api/games/{invite_code}/restore", response_model=SessionAuthResponse)
async def restore_game(invite_code: str, payload: RestoreSessionRequest):
    try:
        session = session_manager.get_session(invite_code)
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err

    try:
        player = session.get_player_by_token(payload.player_token)
    except ValueError as err:
        raise HTTPException(status_code=401, detail=str(err)) from err

    return session.auth_response(player)


@app.get("/api/games/{invite_code}", response_model=SessionSnapshotEvent)
async def get_game(invite_code: str):
    try:
        session = session_manager.get_session(invite_code)
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    return SessionSnapshotEvent(data=session.build_snapshot())


@app.websocket("/api/games/{invite_code}/ws")
async def session_websocket(websocket: WebSocket, invite_code: str, token: str):
    try:
        session = session_manager.get_session(invite_code)
        await session.connect(token, websocket)
    except ValueError:
        await websocket.close(code=1008)
        return

    try:
        while True:
            data = await websocket.receive_json()
            action = ActionRequest(**data)
            try:
                session.apply_action(token, action)
                await session.broadcast_full_state()
            except (PyshitheadError, ValueError) as err:
                message = getattr(err, "message", str(err))
                await session.send_error(token, message)
                await session.send_full_state(session.get_player_by_token(token))
    except WebSocketDisconnect:
        await session.disconnect(token)


@app.websocket("/ws")
async def websocket(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"msg": "Hello WebSocket"})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
