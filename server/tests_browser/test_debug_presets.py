import re
import time

import pytest
from playwright.sync_api import expect

from pyshithead.debug_server import create_debug_app
from pyshithead.models.game import JOKER_RANK, Card, SpecialRank, Suit
from pyshithead.models.session.models import ActionRequest

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


def _open_debug_session(live_app_server_factory, browser_factory, preset_name: str):
    debug_app, seed = create_debug_app(preset_name)
    base_url = live_app_server_factory(debug_app)
    player = seed.session.get_player_by_seat(0)
    page = browser_factory().new_page()

    page.goto(
        f"{base_url}/debug/session?invite={seed.session.invite_code}&token={player.token}",
        wait_until="networkidle",
    )
    expect(page.locator(".connection-indicator")).to_have_class(re.compile(r"\bconnected\b"))
    return page, seed


def _card_id(card: Card) -> str:
    return f"{card.rank}-{int(card.suit)}"


def _click_cards(page, cards):
    for card in cards:
        page.locator(f".hand-fan [data-card-id='{_card_id(card)}']").evaluate(
            "(button) => button.click()"
        )


def _wait_for(predicate, *, timeout=5.0, interval=0.05, message="Timed out waiting for state"):
    deadline = time.monotonic() + timeout
    last_value = None
    while time.monotonic() < deadline:
        last_value = predicate()
        if last_value:
            return last_value
        time.sleep(interval)
    raise AssertionError(f"{message}: {last_value!r}")


def test_debug_bootstrap_link_opens_public_selection_specials_preset(
    live_app_server_factory, browser_factory
):
    page, seed = _open_debug_session(live_app_server_factory, browser_factory, "host-specials-lock")

    expect(page.locator(".dock-prompt")).to_contain_text("Pick 3 public cards for the table.")
    _click_cards(
        page,
        [
            Card(SpecialRank.HIGHLOW, Suit.PIKES),
            Card(JOKER_RANK, Suit.JOKER_RED),
            Card(SpecialRank.BURN, Suit.HEART),
        ],
    )
    expect(page.locator(".hand-fan .card.selected")).to_have_count(3)

    expect(page.locator("#hand-primary-action")).to_be_enabled()
    page.locator("#hand-primary-action").evaluate("(button) => button.click()")

    _wait_for(
        lambda: len(seed.session.build_private_state(0).private_cards) == 3
        and seed.session.build_snapshot().players[0].public_cards is not None
    )
    host_private_state = seed.session.build_private_state(0)
    host_snapshot = next(
        player for player in seed.session.build_snapshot().players if player.seat == 0
    )
    assert len(host_private_state.private_cards) == 3
    assert {card.rank for card in host_private_state.private_cards} == {
        int(SpecialRank.RESET),
        int(SpecialRank.INVISIBLE),
        int(SpecialRank.SKIP),
    }
    assert {card.rank for card in host_snapshot.public_cards} == {
        int(SpecialRank.HIGHLOW),
        JOKER_RANK,
        int(SpecialRank.BURN),
    }


def test_debug_bootstrap_link_opens_revealed_joker_preset_and_resolves_choice(
    live_app_server_factory, browser_factory
):
    page, seed = _open_debug_session(live_app_server_factory, browser_factory, "revealed-joker")

    expect(page.locator(".dock-prompt")).to_contain_text(
        "Choose which rank the revealed joker should be."
    )
    expect(page.locator("[data-joker-rank]")).to_have_count(10)
    page.locator("[data-joker-rank='8']").evaluate("(button) => button.click()")
    expect(page.locator("[data-joker-rank='8']")).to_have_class(re.compile(r"\baccent\b"))

    expect(page.locator("#hand-primary-action")).to_be_enabled()
    seed.session.apply_action(
        seed.session.get_player_by_seat(0).token,
        ActionRequest(type="resolve_joker", choice="", joker_rank=8),
    )
    page.reload(wait_until="networkidle")

    _wait_for(lambda: seed.session.build_snapshot().status_message == "Skip!")
    resolved_private_state = seed.session.build_private_state(0)
    resolved_snapshot = seed.session.build_snapshot()
    assert resolved_private_state.pending_joker_selection is False
    assert resolved_snapshot.pending_joker_selection is False
    assert resolved_snapshot.status_message == "Skip!"
    assert resolved_snapshot.play_pile[0].effective_rank == 8


def test_debug_bootstrap_link_opens_revealed_seven_preset_and_resolves_choice(
    live_app_server_factory, browser_factory
):
    page, seed = _open_debug_session(live_app_server_factory, browser_factory, "revealed-seven")

    expect(page.locator(".dock-prompt")).to_contain_text(
        "Choose how the revealed 7 changes the next player's turn."
    )
    expect(page.locator("#choose-lower")).to_be_visible()
    expect(page.locator("#choose-higher")).to_be_visible()
    page.locator("#choose-lower").click()
    expect(page.locator("#choose-lower")).to_have_class(re.compile(r"\baccent\b"))

    expect(page.locator("#hand-primary-action")).to_be_enabled()
    page.locator("#hand-primary-action").click()

    _wait_for(lambda: seed.session.build_snapshot().status_message == "7 or lower!")
    expect(page.locator(".dock-error")).to_have_count(0)
    expect(page.locator(".dock-prompt")).to_contain_text("Waiting for Guest to play.")
    resolved_private_state = seed.session.build_private_state(0)
    resolved_snapshot = seed.session.build_snapshot()
    assert resolved_private_state.pending_joker_selection is False
    assert resolved_snapshot.pending_joker_selection is False
    assert resolved_snapshot.status_message == "7 or lower!"
    assert resolved_snapshot.current_turn_seat == 1


@pytest.mark.skip(reason="TODO: debug hidden-seven-take bootstrap reconnect issue")
def test_debug_bootstrap_link_opens_hidden_seven_take_preset(
    live_app_server_factory, browser_factory
):
    page, seed = _open_debug_session(live_app_server_factory, browser_factory, "hidden-seven-take")

    expect(page.locator(".dock-prompt")).to_contain_text("Take the pile")
    expect(page.locator(".pile-preview")).to_contain_text("7")
    expect(page.locator("#take-pile-overlay")).to_be_visible()
    assert seed.session.build_snapshot().status_message == "Host revealed 7 and must take the pile."
