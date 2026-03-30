import pytest
from playwright.sync_api import expect

from pyshithead.debug_server import create_debug_app

pytestmark = pytest.mark.browser


def test_debug_bootstrap_link_opens_hidden_take_preset(live_app_server_factory, browser_factory):
    debug_app, seed = create_debug_app("hidden-take")
    base_url = live_app_server_factory(debug_app)
    player = seed.session.get_player_by_seat(0)
    page = browser_factory().new_page()

    page.goto(
        f"{base_url}/debug/session?invite={seed.session.invite_code}&token={player.token}",
        wait_until="networkidle",
    )
    expect(page.locator(".hand-dock")).to_be_visible()

    expect(page.locator(".dock-prompt")).to_contain_text("Take the pile")
    expect(page.locator(".pile-preview")).to_contain_text("4")
    expect(page.locator("#take-pile-overlay")).to_be_visible()
