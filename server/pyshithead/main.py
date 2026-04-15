"""
start server with
uvicorn pyshithead.main:app --reload
"""

import json
import logging
import secrets
from html import escape
from pathlib import Path
from urllib.parse import urlencode

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse
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
SITE_THEME_COLOR = "#11231f"
HOME_TITLE = "Play Shithead Online | Multiplayer Card Game"
HOME_DESCRIPTION = (
    "Play Shithead online with friends in your browser. Create a table, join a game, "
    "learn the rules, and start playing instantly."
)
RULES_TITLE = "Shithead Rules | Quick Guide"
RULES_DESCRIPTION = (
    "Learn the short rules for Shithead, including special cards, turn flow, and how "
    "to avoid being the last player with cards."
)
PLAY_TITLE = "Play Shithead Online | Browser Table"
PLAY_DESCRIPTION = "Create or join a private Shithead table in your browser."


def _absolute_url(request: Request, path: str) -> str:
    return f"{str(request.base_url).rstrip('/')}{path}"


def _play_href(*, invite_code: str | None = None, mode: str | None = None) -> str:
    query = {
        key: value
        for key, value in {
            "invite": invite_code.strip().upper() if invite_code else None,
            "mode": mode if mode in {"create", "join"} else None,
        }.items()
        if value
    }
    if not query:
        return "/play"
    return f"/play?{urlencode(query)}"


def _render_meta_tags(
    *,
    title: str,
    description: str,
    canonical_url: str,
    robots: str,
    og_type: str = "website",
    structured_data: list[dict] | None = None,
) -> str:
    title_attr = escape(title, quote=True)
    description_attr = escape(description, quote=True)
    canonical_attr = escape(canonical_url, quote=True)
    robots_attr = escape(robots, quote=True)
    tags = [
        f"    <title>{escape(title)}</title>",
        f'    <meta name="description" content="{description_attr}" />',
        f'    <meta name="robots" content="{robots_attr}" />',
        f'    <link rel="canonical" href="{canonical_attr}" />',
        f'    <meta property="og:type" content="{escape(og_type, quote=True)}" />',
        f'    <meta property="og:title" content="{title_attr}" />',
        f'    <meta property="og:description" content="{description_attr}" />',
        f'    <meta property="og:url" content="{canonical_attr}" />',
        '    <meta property="og:site_name" content="Shithead" />',
        '    <meta name="twitter:card" content="summary" />',
    ]
    if structured_data:
        tags.extend(
            [
                '    <script type="application/ld+json">'
                f"{json.dumps(item, separators=(',', ':'))}"
                "</script>"
                for item in structured_data
            ]
        )
    return "\n".join(tags)


def _render_public_document(
    *,
    request: Request,
    title: str,
    description: str,
    canonical_path: str,
    body_html: str,
    robots: str = "index,follow",
    structured_data: list[dict] | None = None,
) -> str:
    canonical_url = _absolute_url(request, canonical_path)
    meta_tags = _render_meta_tags(
        title=title,
        description=description,
        canonical_url=canonical_url,
        robots=robots,
        structured_data=structured_data,
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <meta name="theme-color" content="{SITE_THEME_COLOR}" />
{meta_tags}
    <link rel="icon" type="image/png" sizes="192x192" href="/static/icons/icon-192.png?v={STATIC_ASSET_VERSION}" />
    <link rel="apple-touch-icon" href="/static/icons/icon-180.png?v={STATIC_ASSET_VERSION}" />
    <link rel="manifest" href="/static/manifest.webmanifest?v={STATIC_ASSET_VERSION}" />
    <link rel="stylesheet" href="/static/public.css?v={STATIC_ASSET_VERSION}" />
  </head>
  <body class="public-body">
    {body_html}
  </body>
</html>"""


def _render_app_shell_document(
    *,
    request: Request,
    title: str,
    description: str,
    robots: str = "noindex, nofollow",
    bootstrap_script: str = "",
) -> str:
    canonical_url = _absolute_url(request, "/play")
    meta_tags = _render_meta_tags(
        title=title,
        description=description,
        canonical_url=canonical_url,
        robots=robots,
    )
    bootstrap_markup = ""
    if bootstrap_script:
        bootstrap_markup = f"""
    <script>
      {bootstrap_script}
    </script>"""
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <meta name="theme-color" content="{SITE_THEME_COLOR}" />
{meta_tags}
    <link rel="icon" type="image/png" sizes="192x192" href="/static/icons/icon-192.png?v={STATIC_ASSET_VERSION}" />
    <link rel="apple-touch-icon" href="/static/icons/icon-180.png?v={STATIC_ASSET_VERSION}" />
    <link rel="manifest" href="/static/manifest.webmanifest?v={STATIC_ASSET_VERSION}" />
    <link rel="stylesheet" href="/static/styles.css?v={STATIC_ASSET_VERSION}" />
  </head>
  <body>
{bootstrap_markup}
    <div class="page-shell">
      <main id="app" class="app-root"></main>
    </div>
    <div id="motion-overlay" class="motion-overlay" aria-hidden="true">
      <div id="motion-layer-host" class="motion-layer"></div>
    </div>
    <script type="module" src="/static/app.js?v={STATIC_ASSET_VERSION}"></script>
  </body>
</html>"""


def _render_homepage(request: Request) -> str:
    create_href = _play_href(mode="create")
    join_href = _play_href(mode="join")
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": "Can I play on mobile?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Yes, the game works on desktop and mobile browsers.",
                },
            },
            {
                "@type": "Question",
                "name": "Do I need an account?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "No, you can create or join a table directly.",
                },
            },
            {
                "@type": "Question",
                "name": "Can I play with friends?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Yes, create a table and share the code or link.",
                },
            },
        ],
    }
    website_schema = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Shithead",
        "url": _absolute_url(request, "/"),
    }
    body_html = f"""
    <div class="public-page-shell">
      <header class="site-header">
        <a class="site-brand" href="/">Shithead</a>
        <nav class="site-nav" aria-label="Primary">
          <a href="/rules">Rules</a>
          <a href="/play">Play</a>
        </nav>
      </header>
      <main class="site-main">
        <section class="hero-card">
          <p class="eyebrow">Browser multiplayer card game</p>
          <h1>Play Shithead Online</h1>
          <p class="lede">Play Shithead with friends right in your browser. No install, no signup, just create a table or join one and start playing.</p>
          <div class="cta-row">
            <a class="button-link button-link-primary" href="{create_href}">Create Table</a>
            <a class="button-link button-link-secondary" href="{join_href}">Join Table</a>
          </div>
          <p class="microcopy">Also known as Palace, Karma, or Shed.</p>
        </section>
        <section class="content-grid">
          <article class="content-card">
            <h2>Quick to learn, fun to master</h2>
            <p>Get rid of all your cards before everyone else. Play higher or matching cards, use special cards at the right moment, and survive long enough to avoid becoming the Shithead.</p>
          </article>
          <article class="content-card">
            <h2>How to play</h2>
            <p>Each player starts with hand cards, visible table cards, and hidden table cards. On your turn, play valid cards onto the pile. When your hand is gone, continue with your visible cards, then your hidden cards. The last player left with cards loses.</p>
            <p><a class="text-link" href="/rules">Read the short rules</a></p>
          </article>
        </section>
        <section class="content-card">
          <h2>Special cards</h2>
          <dl class="detail-grid">
            <div>
              <dt>2 &mdash; Reset</dt>
              <dd>Resets the pile so the next player can start fresh.</dd>
            </div>
            <div>
              <dt>5 &mdash; Transparent</dt>
              <dd>Transparent card with special behavior in the turn order.</dd>
            </div>
            <div>
              <dt>7 &mdash; Higher or lower</dt>
              <dd>Choose whether the next player has to play higher or lower.</dd>
            </div>
            <div>
              <dt>8 &mdash; Skip</dt>
              <dd>Skips the next player.</dd>
            </div>
            <div>
              <dt>10 &mdash; Burn</dt>
              <dd>Burns the pile immediately.</dd>
            </div>
            <div>
              <dt>Joker &mdash; Wild</dt>
              <dd>Can be anything except 2, 5, or 10.</dd>
            </div>
          </dl>
          <p class="rules-note"><strong>Rules note:</strong> 2, 5, and 10 can be played on every card. Exception: if a 7 is active, the next card must follow the higher/lower restriction.</p>
        </section>
        <section class="content-card">
          <h2>FAQ</h2>
          <dl class="faq-list">
            <div>
              <dt>Can I play on mobile?</dt>
              <dd>Yes, the game works on desktop and mobile browsers.</dd>
            </div>
            <div>
              <dt>Do I need an account?</dt>
              <dd>No, you can create or join a table directly.</dd>
            </div>
            <div>
              <dt>Can I play with friends?</dt>
              <dd>Yes, create a table and share the code or link.</dd>
            </div>
          </dl>
        </section>
        <section class="content-card content-card-cta">
          <h2>Ready to play?</h2>
          <div class="cta-row">
            <a class="button-link button-link-primary" href="{create_href}">Create Table</a>
            <a class="button-link button-link-secondary" href="{join_href}">Join Table</a>
          </div>
        </section>
      </main>
    </div>
    """
    return _render_public_document(
        request=request,
        title=HOME_TITLE,
        description=HOME_DESCRIPTION,
        canonical_path="/",
        body_html=body_html,
        structured_data=[website_schema, faq_schema],
    )


def _render_rules_page(request: Request) -> str:
    body_html = f"""
    <div class="public-page-shell">
      <header class="site-header">
        <a class="site-brand" href="/">Shithead</a>
        <nav class="site-nav" aria-label="Primary">
          <a href="/">Home</a>
          <a href="/play">Play</a>
        </nav>
      </header>
      <main class="site-main site-main-narrow">
        <section class="hero-card hero-card-compact">
          <p class="eyebrow">Short rules</p>
          <h1>How to play Shithead</h1>
          <p class="lede">A quick guide for starting a table and learning the flow without digging through a long rules article.</p>
        </section>
        <section class="content-card">
          <h2>Setup</h2>
          <p>Each player starts with hand cards, visible table cards, and hidden table cards. Play starts from the hand, then visible table cards, then hidden table cards.</p>
        </section>
        <section class="content-card">
          <h2>Your turn</h2>
          <p>Play valid cards onto the pile. In general you play matching or higher ranks, unless a special card changes the rule. If you cannot play, you take the pile.</p>
        </section>
        <section class="content-card">
          <h2>Special cards</h2>
          <ul class="scan-list">
            <li><strong>2</strong> resets the pile.</li>
            <li><strong>5</strong> is transparent and uses its special turn-order behavior.</li>
            <li><strong>7</strong> forces the next player to go higher or lower, depending on the choice.</li>
            <li><strong>8</strong> skips the next player.</li>
            <li><strong>10</strong> burns the pile immediately.</li>
            <li><strong>Joker</strong> is wild, except it cannot stand in for 2, 5, or 10.</li>
          </ul>
          <p class="rules-note"><strong>Rules note:</strong> 2, 5, and 10 can be played on every card. Exception: if a 7 is active, the next card must follow the higher/lower restriction.</p>
        </section>
        <section class="content-card">
          <h2>Winning and losing</h2>
          <p>Get rid of all your cards before everyone else. The last player left with cards loses and becomes the Shithead.</p>
        </section>
        <section class="content-card content-card-cta">
          <h2>Ready to play?</h2>
          <div class="cta-row">
            <a class="button-link button-link-primary" href="{_play_href(mode='create')}">Create Table</a>
            <a class="button-link button-link-secondary" href="{_play_href(mode='join')}">Join Table</a>
          </div>
        </section>
      </main>
    </div>
    """
    return _render_public_document(
        request=request,
        title=RULES_TITLE,
        description=RULES_DESCRIPTION,
        canonical_path="/rules",
        body_html=body_html,
    )


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
    async def read_homepage(request: Request):
        invite_code = request.query_params.get("invite")
        mode = request.query_params.get("mode")
        if invite_code or mode in {"create", "join"}:
            return RedirectResponse(url=_play_href(invite_code=invite_code, mode=mode))
        return HTMLResponse(_render_homepage(request))

    @app.get("/play", response_class=HTMLResponse)
    @app.get("/play/", include_in_schema=False, response_class=HTMLResponse)
    async def read_play(request: Request):
        return HTMLResponse(
            _render_app_shell_document(
                request=request,
                title=PLAY_TITLE,
                description=PLAY_DESCRIPTION,
            ),
            headers={"X-Robots-Tag": "noindex, nofollow"},
        )

    @app.get("/rules", response_class=HTMLResponse)
    @app.get("/rules/", include_in_schema=False, response_class=HTMLResponse)
    async def read_rules(request: Request):
        return HTMLResponse(_render_rules_page(request))

    @app.get("/healthz")
    async def healthcheck():
        return {"ok": True}

    @app.get("/robots.txt", include_in_schema=False)
    async def read_robots(request: Request):
        robots = "\n".join(
            [
                "User-agent: *",
                "Allow: /",
                "Disallow: /api/",
                "Disallow: /debug/",
                "Disallow: /stats",
                "Disallow: /stats-ui",
                f"Sitemap: {_absolute_url(request, '/sitemap.xml')}",
            ]
        )
        return PlainTextResponse(robots)

    @app.get("/sitemap.xml", include_in_schema=False)
    async def read_sitemap(request: Request):
        urls = [
            _absolute_url(request, "/"),
            _absolute_url(request, "/rules"),
        ]
        body = "".join(f"<url><loc>{escape(url)}</loc></url>" for url in urls)
        return Response(
            content=(
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f"{body}"
                "</urlset>"
            ),
            media_type="application/xml",
        )

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
        async def debug_session_bootstrap(request: Request, invite: str, token: str):
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
            return HTMLResponse(
                _render_app_shell_document(
                    request=request,
                    title="Shithead Debug",
                    description="Debug bootstrap for the Shithead game client.",
                    bootstrap_script=(
                        "localStorage.setItem("
                        f"{json.dumps(SESSION_STORAGE_KEY)}, "
                        f"JSON.stringify({json.dumps(payload)}));"
                    ),
                ),
                headers={"X-Robots-Tag": "noindex, nofollow"},
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
