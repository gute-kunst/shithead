import socket
import threading
import time

import httpx
import pytest
import uvicorn
from playwright.sync_api import sync_playwright

from pyshithead.main import app, session_manager


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _start_server(target_app):
    host = "127.0.0.1"
    port = _find_free_port()
    config = uvicorn.Config(
        target_app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://{host}:{port}"
    deadline = time.time() + 15
    last_error = None
    while time.time() < deadline:
        try:
            response = httpx.get(f"{base_url}/healthz", timeout=1.0)
            if response.status_code == 200:
                return server, thread, base_url
        except httpx.HTTPError as err:
            last_error = err
        time.sleep(0.1)

    server.should_exit = True
    thread.join(timeout=5)
    raise RuntimeError(f"Timed out waiting for test server to start: {last_error}")


@pytest.fixture(autouse=True)
def clear_sessions():
    session_manager.sessions.clear()
    yield
    session_manager.sessions.clear()


@pytest.fixture(scope="session")
def live_server():
    server, thread, base_url = _start_server(app)

    yield base_url

    server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture
def live_app_server_factory():
    servers = []

    def factory(target_app):
        server, thread, base_url = _start_server(target_app)
        servers.append((server, thread))
        return base_url

    yield factory

    for server, thread in servers:
        server.should_exit = True
        thread.join(timeout=10)


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
def browser(playwright_instance):
    browser = playwright_instance.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture
def browser_factory(browser):
    contexts = []

    def factory():
        context = browser.new_context(
            service_workers="allow",
            viewport={"width": 430, "height": 932},
        )
        contexts.append(context)
        return context

    yield factory

    for context in contexts:
        context.close()


@pytest.fixture
def touch_browser_factory(browser):
    contexts = []

    def factory():
        context = browser.new_context(
            service_workers="allow",
            viewport={"width": 375, "height": 812},
            is_mobile=True,
            has_touch=True,
            device_scale_factor=2,
        )
        contexts.append(context)
        return context

    yield factory

    for context in contexts:
        context.close()
