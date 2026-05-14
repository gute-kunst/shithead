import socket
import threading
import time

import httpx
import pytest
import uvicorn
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from pyshithead.main import app, session_manager

BROWSER_TYPES = ("chromium", "firefox", "webkit")
BROWSER_PROFILES = {
    "desktop": {
        "viewport": {"width": 1440, "height": 900},
        "is_mobile": False,
        "has_touch": False,
        "device_scale_factor": 1,
    },
    "mobile_portrait": {
        "viewport": {"width": 390, "height": 844},
        "is_mobile": True,
        "has_touch": True,
        "device_scale_factor": 2,
    },
    "mobile_landscape": {
        "viewport": {"width": 844, "height": 390},
        "is_mobile": True,
        "has_touch": True,
        "device_scale_factor": 2,
    },
}

BROWSER_PROFILES_BY_BROWSER = {
    "chromium": set(BROWSER_PROFILES),
    "webkit": set(BROWSER_PROFILES),
    "firefox": {"desktop"},
}


def _selected_browsers(config) -> tuple[str, ...]:
    return tuple(config.getoption("browser") or list(BROWSER_TYPES))


def _supported_browser_profile_pairs(selected_browsers: tuple[str, ...]) -> list[tuple[str, str]]:
    return [
        (browser_name, profile_name)
        for browser_name in selected_browsers
        for profile_name in BROWSER_PROFILES
        if profile_name in BROWSER_PROFILES_BY_BROWSER[browser_name]
    ]


def pytest_addoption(parser):
    parser.addoption(
        "--browser",
        action="append",
        choices=BROWSER_TYPES,
        help="Limit browser test execution to the selected browser type(s).",
    )


def pytest_generate_tests(metafunc):
    selected_browsers = _selected_browsers(metafunc.config)
    fixture_names = set(metafunc.fixturenames)

    if "browser_factory" in fixture_names:
        pairs = _supported_browser_profile_pairs(selected_browsers)
        metafunc.parametrize(
            ("browser_name", "browser_profile_name"),
            pairs,
            scope="session",
            ids=[f"{profile_name}-{browser_name}" for browser_name, profile_name in pairs],
        )
        return

    if "desktop_browser_factory" in fixture_names:
        metafunc.parametrize("browser_name", selected_browsers, scope="session", ids=selected_browsers)
        return

    if "touch_browser_factory" in fixture_names:
        touch_browsers = [
            browser_name
            for browser_name in selected_browsers
            if "mobile_portrait" in BROWSER_PROFILES_BY_BROWSER[browser_name]
        ]
        metafunc.parametrize("browser_name", touch_browsers, scope="session", ids=touch_browsers)
        return

    if "mobile_landscape_browser_factory" in fixture_names:
        landscape_browsers = [
            browser_name
            for browser_name in selected_browsers
            if "mobile_landscape" in BROWSER_PROFILES_BY_BROWSER[browser_name]
        ]
        metafunc.parametrize(
            "browser_name",
            landscape_browsers,
            scope="session",
            ids=landscape_browsers,
        )


def pytest_collection_modifyitems(config, items):
    selected_browsers = set(_selected_browsers(config))
    selected_items = []
    deselected_items = []
    supports_touch = any(
        "mobile_portrait" in BROWSER_PROFILES_BY_BROWSER[browser_name]
        for browser_name in selected_browsers
    )
    supports_mobile_landscape = any(
        "mobile_landscape" in BROWSER_PROFILES_BY_BROWSER[browser_name]
        for browser_name in selected_browsers
    )
    for item in items:
        if item.get_closest_marker("chromium_only") and "chromium" not in selected_browsers:
            deselected_items.append(item)
        elif "touch_browser_factory" in item.fixturenames and not supports_touch:
            deselected_items.append(item)
        elif (
            "mobile_landscape_browser_factory" in item.fixturenames
            and not supports_mobile_landscape
        ):
            deselected_items.append(item)
        else:
            selected_items.append(item)
    if deselected_items:
        config.hook.pytest_deselected(items=deselected_items)
        items[:] = selected_items


def _browser_launch(browser_type, *, browser_name: str):
    try:
        return getattr(browser_type, browser_name).launch(headless=True)
    except PlaywrightError as err:
        if "Executable doesn't exist" in str(err) or "browser has not been installed" in str(err):
            pytest.skip(f"Playwright browser '{browser_name}' is not installed.")
        raise


def _create_browser_context(browser, *, profile_name: str):
    context = browser.new_context(
        service_workers="allow",
        **BROWSER_PROFILES[profile_name],
    )
    return context


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
    manager = sync_playwright()
    try:
        playwright = manager.__enter__()
    except PermissionError as err:
        try:
            manager.__exit__(PermissionError, err, err.__traceback__)
        finally:
            pytest.skip(f"Playwright could not start in this environment: {err}")
    try:
        yield playwright
    finally:
        manager.__exit__(None, None, None)


@pytest.fixture(scope="session")
def browser_name(request):
    return request.param


@pytest.fixture(scope="session")
def browser(playwright_instance, browser_name):
    browser = _browser_launch(playwright_instance, browser_name=browser_name)
    yield browser
    browser.close()


@pytest.fixture(scope="session")
def browser_profile_name(request):
    return request.param


def _context_factory(browser, *, profile_name: str):
    contexts = []

    def factory():
        context = _create_browser_context(browser, profile_name=profile_name)
        contexts.append(context)
        return context

    return factory, contexts


@pytest.fixture
def browser_factory(browser, browser_profile_name):
    factory, contexts = _context_factory(browser, profile_name=browser_profile_name)
    yield factory

    for context in contexts:
        context.close()


@pytest.fixture
def desktop_browser_factory(browser):
    factory, contexts = _context_factory(browser, profile_name="desktop")
    yield factory

    for context in contexts:
        context.close()


@pytest.fixture
def touch_browser_factory(browser):
    factory, contexts = _context_factory(browser, profile_name="mobile_portrait")
    yield factory

    for context in contexts:
        context.close()


@pytest.fixture
def mobile_landscape_browser_factory(browser):
    factory, contexts = _context_factory(browser, profile_name="mobile_landscape")
    yield factory

    for context in contexts:
        context.close()


@pytest.fixture
def chromium_browser(playwright_instance):
    browser = playwright_instance.chromium.launch(headless=True)
    yield browser
    browser.close()
