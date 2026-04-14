"""
start server with
uvicorn pyshithead.main:app --reload
"""

import json
import logging
import secrets
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from pyshithead.models.game import PyshitheadError
from pyshithead.models.session import (
    ActionRequest,
    CreateGameRequest,
    GameSessionManager,
    JoinGameRequest,
    KickPlayerRequest,
    RematchRequest,
    RestoreSessionRequest,
    SessionAuthResponse,
    SessionSnapshotEvent,
    StartGameRequest,
    UpdateSettingsRequest,
)

app = FastAPI()

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATS_UI_DIR = Path(__file__).resolve().parent / "stats_ui"
SESSION_STORAGE_KEY = "shithead.alpha.session"
ANONYMOUS_USER_COOKIE = "shithead.alpha.user"
STATIC_ASSET_VERSION = "20260405b"


def _http_error(err: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(err))


def _resolve_user_id(request: Request, response: Response) -> str:
    user_id = request.cookies.get(ANONYMOUS_USER_COOKIE)
    if user_id:
        return user_id

    user_id = secrets.token_urlsafe(16)
    response.set_cookie(
        ANONYMOUS_USER_COOKIE,
        user_id,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=60 * 60 * 24 * 365,
        path="/",
    )
    return user_id


def create_app(
    *,
    session_manager: GameSessionManager | None = None,
    enable_debug_bootstrap: bool = False,
) -> FastAPI:
    managed_sessions = session_manager or GameSessionManager()
    app = FastAPI()
    app.state.session_manager = managed_sessions
    app.state.debug_bootstrap_enabled = enable_debug_bootstrap
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def read_main():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/healthz")
    async def healthcheck():
        return {"ok": True}

    @app.get("/stats-ui", response_class=HTMLResponse)
    @app.get("/stats-ui/", include_in_schema=False)
    async def read_stats_ui():
        return FileResponse(STATS_UI_DIR / "index.html")

    @app.get("/stats-ui/stats.js", include_in_schema=False)
    async def read_stats_ui_script():
        return FileResponse(STATS_UI_DIR / "stats.js", media_type="application/javascript")

    @app.get("/stats-ui/styles.css", include_in_schema=False)
    async def read_stats_ui_styles():
        return FileResponse(STATS_UI_DIR / "styles.css", media_type="text/css")

    @app.get("/stats")
    async def read_stats(days: int = Query(30, ge=7, le=365)):
        return managed_sessions.get_stats(days=days)

    if enable_debug_bootstrap:

        @app.get("/debug/session", response_class=HTMLResponse)
        async def debug_session_bootstrap(invite: str, token: str):
            try:
                session = managed_sessions.get_session(invite)
                player = session.get_player_by_token(token)
            except ValueError as err:
                raise HTTPException(status_code=404, detail=str(err)) from err
            payload = {
                "inviteCode": session.invite_code,
                "playerToken": player.token,
                "seat": player.seat,
                "displayName": player.display_name,
            }
            payload_json = json.dumps(payload)
            return HTMLResponse(
                f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <meta name="theme-color" content="#11231f" />
    <title>Shithead Debug</title>
    <link rel="icon" type="image/png" sizes="192x192" href="/static/icons/icon-192.png?v={STATIC_ASSET_VERSION}" />
    <link rel="apple-touch-icon" href="/static/icons/icon-180.png?v={STATIC_ASSET_VERSION}" />
    <link rel="manifest" href="/static/manifest.webmanifest?v={STATIC_ASSET_VERSION}" />
    <link rel="stylesheet" href="/static/styles.css?v={STATIC_ASSET_VERSION}" />
  </head>
  <body>
    <script>
      localStorage.setItem({json.dumps(SESSION_STORAGE_KEY)}, JSON.stringify({payload_json}));
    </script>
    <div class="page-shell">
      <main id="app" class="app-root"></main>
    </div>
    <div id="motion-overlay" class="motion-overlay" aria-hidden="true">
      <div id="motion-layer-host" class="motion-layer"></div>
    </div>
    <script type="module" src="/static/app.js?v={STATIC_ASSET_VERSION}"></script>
  </body>
</html>"""
            )

    @app.post("/api/games", response_model=SessionAuthResponse)
    async def create_game(payload: CreateGameRequest, request: Request, response: Response):
        user_id = _resolve_user_id(request, response)
        try:
            session = managed_sessions.create_session(payload.display_name, creator_user_id=user_id)
        except ValueError as err:
            raise _http_error(err) from err
        return session.auth_response(session.get_player_by_token(session.host_token))

    @app.post("/api/games/{invite_code}/join", response_model=SessionAuthResponse)
    async def join_game(
        invite_code: str,
        payload: JoinGameRequest,
        request: Request,
        response: Response,
    ):
        user_id = _resolve_user_id(request, response)
        try:
            session = managed_sessions.get_session(invite_code)
            player = session.join(payload.display_name)
        except ValueError as err:
            raise _http_error(err) from err
        managed_sessions.note_user_seen(user_id)
        await session.broadcast_snapshot()
        return session.auth_response(player)

    @app.post("/api/games/{invite_code}/start", response_model=SessionSnapshotEvent)
    async def start_game(invite_code: str, payload: StartGameRequest):
        try:
            session = managed_sessions.get_session(invite_code)
            session.start(payload.player_token)
        except ValueError as err:
            raise _http_error(err) from err
        await session.broadcast_full_state()
        return SessionSnapshotEvent(data=session.build_snapshot())

    @app.post("/api/games/{invite_code}/rematch", response_model=SessionSnapshotEvent)
    async def rematch_game(invite_code: str, payload: RematchRequest):
        try:
            session = managed_sessions.get_session(invite_code)
            session.rematch(payload.player_token)
        except ValueError as err:
            raise _http_error(err) from err
        await session.broadcast_full_state()
        return SessionSnapshotEvent(data=session.build_snapshot())

    @app.post("/api/games/{invite_code}/settings", response_model=SessionSnapshotEvent)
    async def update_game_settings(invite_code: str, payload: UpdateSettingsRequest):
        try:
            session = managed_sessions.get_session(invite_code)
            session.update_settings(
                payload.player_token,
                allow_optional_take_pile=payload.allow_optional_take_pile,
            )
        except ValueError as err:
            raise _http_error(err) from err
        await session.broadcast_snapshot()
        return SessionSnapshotEvent(data=session.build_snapshot())

    @app.post("/api/games/{invite_code}/restore", response_model=SessionAuthResponse)
    async def restore_game(
        invite_code: str,
        payload: RestoreSessionRequest,
        request: Request,
        response: Response,
    ):
        user_id = _resolve_user_id(request, response)
        try:
            session = managed_sessions.get_session(invite_code)
        except ValueError as err:
            raise HTTPException(status_code=404, detail=str(err)) from err

        try:
            player = session.get_player_by_token(payload.player_token)
        except ValueError as err:
            raise HTTPException(status_code=401, detail=str(err)) from err

        managed_sessions.note_user_seen(user_id)
        return session.auth_response(player)

    @app.post("/api/games/{invite_code}/players/{seat}/kick", response_model=SessionSnapshotEvent)
    async def kick_player(invite_code: str, seat: int, payload: KickPlayerRequest):
        try:
            session = managed_sessions.get_session(invite_code)
            session.kick_player(payload.player_token, seat)
        except ValueError as err:
            raise _http_error(err) from err
        await session.broadcast_full_state()
        return SessionSnapshotEvent(data=session.build_snapshot())

    @app.get("/api/games/{invite_code}", response_model=SessionSnapshotEvent)
    async def get_game(invite_code: str):
        try:
            session = managed_sessions.get_session(invite_code)
        except ValueError as err:
            raise HTTPException(status_code=404, detail=str(err)) from err
        return SessionSnapshotEvent(data=session.build_snapshot())

    @app.websocket("/api/games/{invite_code}/ws")
    async def session_websocket(websocket: WebSocket, invite_code: str, token: str):
        user_id = websocket.cookies.get(ANONYMOUS_USER_COOKIE)
        try:
            session = managed_sessions.get_session(invite_code)
            await session.connect(token, websocket)
            managed_sessions.note_user_seen(user_id)
        except ValueError as err:
            logger.info("Rejected websocket connection for invite %s: %s", invite_code, err)
            await websocket.close(code=1008)
            return

        try:
            while True:
                data = await websocket.receive_json()
                action = ActionRequest(**data)
                try:
                    shoutout_event = session.apply_action(token, action)
                    managed_sessions.note_user_seen(user_id)
                    if shoutout_event is not None:
                        await session.broadcast_shoutout(shoutout_event)
                        await session.send_private_state(session.get_player_by_token(token))
                    else:
                        await session.broadcast_full_state()
                except (PyshitheadError, ValueError) as err:
                    message = getattr(err, "message", str(err))
                    await session.send_error(token, message)
                    await session.send_full_state(session.get_player_by_token(token))
        except WebSocketDisconnect:
            await session.disconnect(token)

    return app


session_manager = GameSessionManager()
app = create_app(session_manager=session_manager)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
