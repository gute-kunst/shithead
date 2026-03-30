import re

import pytest
from playwright.sync_api import expect

from pyshithead.main import session_manager
from pyshithead.models.game import Card, PileOfCards, SetOfCards, Suit
from pyshithead.models.session.models import ActionRequest

pytestmark = pytest.mark.browser


def open_page(context, base_url: str, path: str = "/"):
    page = context.new_page()
    page.goto(f"{base_url}{path}", wait_until="networkidle")
    return page


def expand_bucket(page, bucket: str):
    toggle = page.locator(f"[data-landing-bucket='{bucket}']")
    expect(toggle).to_be_visible()
    if toggle.get_attribute("aria-expanded") != "true":
        toggle.click()
    return toggle


def create_table(page, display_name: str):
    expand_bucket(page, "create")
    page.locator("#create-name").fill(display_name)
    page.get_by_role("button", name="Create game").click()
    expect(page.locator("#copy-invite-code")).to_be_visible()


def join_table(page, invite_code: str, display_name: str):
    expand_bucket(page, "join")
    page.locator("#join-code").fill(invite_code)
    page.locator("#join-name").fill(display_name)
    page.get_by_role("button", name="Join game").click()
    expect(page.get_by_role("button", name="Leave")).to_be_visible()


def extract_invite_code(page) -> str:
    invite_text = page.locator("#copy-invite-code").text_content() or ""
    match = re.search(r"Invite code ([A-Z0-9]{6})", invite_text)
    assert match is not None
    return match.group(1)


def choose_public_cards(page):
    cards = page.locator(".hand-fan [data-card-id]")
    expect(cards).to_have_count(6)
    for index in range(3):
        cards.nth(index).click()
    page.locator("#hand-primary-action").click()


def wait_until_public_selection_finished(page):
    page.wait_for_function(
        """
        () => {
          const prompt = document.querySelector(".dock-prompt");
          return prompt && !prompt.textContent.includes("Pick 3 public cards for the table.");
        }
        """
    )


def test_landing_shows_folded_buckets_and_rules_menu(live_server, browser_factory):
    page = open_page(browser_factory(), live_server)

    expect(page.get_by_text("Shithead")).to_be_visible()
    expect(page.locator("[data-landing-bucket='create']")).to_have_attribute(
        "aria-expanded", "false"
    )
    expect(page.locator("[data-landing-bucket='join']")).to_have_attribute("aria-expanded", "false")

    page.locator("#open-rules-menu").click()
    expect(page.locator(".rules-menu")).to_contain_text("How to play")
    page.locator("#close-rules-menu").click()
    expect(page.locator(".rules-menu")).to_have_count(0)


def test_invite_link_prefills_and_prioritizes_join(live_server, browser_factory):
    page = open_page(browser_factory(), live_server, "/?invite=ABC123")

    expect(page.locator("[data-landing-bucket='join']")).to_have_attribute("aria-expanded", "true")
    expect(page.locator("#join-code")).to_have_value("ABC123")
    expect(page.locator(".landing-form-row .landing-table-card").first).to_contain_text(
        "Join a table"
    )


def test_multiplayer_lobby_start_public_selection_and_refresh_reconnect(
    live_server, browser_factory
):
    host_page = open_page(browser_factory(), live_server)
    create_table(host_page, "Host")
    invite_code = extract_invite_code(host_page)

    guest_page = open_page(browser_factory(), live_server)
    join_table(guest_page, invite_code, "Guest")

    expect(host_page.get_by_text("Guest")).to_be_visible()
    host_page.locator("#start-game").click()

    expect(host_page.locator(".dock-prompt")).to_contain_text("Pick 3 public cards for the table.")
    expect(guest_page.locator(".dock-prompt")).to_contain_text("Pick 3 public cards for the table.")

    choose_public_cards(host_page)
    choose_public_cards(guest_page)

    wait_until_public_selection_finished(host_page)
    wait_until_public_selection_finished(guest_page)

    guest_page.reload(wait_until="networkidle")
    expect(guest_page.locator(".hand-dock")).to_be_visible()
    expect(guest_page.get_by_text("Your hand")).to_be_visible()
    guest_page.wait_for_function(
        """
        () => {
          const stored = window.localStorage.getItem("shithead.alpha.session");
          return stored && JSON.parse(stored).inviteCode;
        }
        """
    )


def test_lobby_optional_take_setting_syncs_and_shows_take_pile_action(live_server, browser_factory):
    host_page = open_page(browser_factory(), live_server)
    create_table(host_page, "Host")
    invite_code = extract_invite_code(host_page)

    guest_page = open_page(browser_factory(), live_server)
    join_table(guest_page, invite_code, "Guest")

    host_toggle = host_page.locator("#toggle-optional-take-pile")
    guest_indicator = guest_page.locator(".lobby-setting-indicator")

    expect(host_toggle).to_have_attribute("aria-checked", "false")
    expect(guest_indicator).to_contain_text("Off")

    host_toggle.click()

    expect(host_toggle).to_have_attribute("aria-checked", "true")
    expect(guest_page.locator(".lobby-setting-indicator")).to_contain_text("On")

    host_page.locator("#start-game").click()
    choose_public_cards(host_page)
    choose_public_cards(guest_page)
    wait_until_public_selection_finished(host_page)
    wait_until_public_selection_finished(guest_page)

    session = session_manager.get_session(invite_code)
    game = session.game_manager.game
    game.play_pile = PileOfCards([Card(9, Suit.HEART)])
    game.valid_ranks = {9}
    host_player = game.get_player(0)
    host_player.private_cards = SetOfCards([Card(9, Suit.CLOVERS)])

    host_page.reload(wait_until="networkidle")

    expect(host_page.locator("#take-pile-overlay")).to_be_visible()
    expect(host_page.locator(".dock-prompt")).to_contain_text("take the pile")


def test_service_worker_registers_and_reload_keeps_app_usable(live_server, browser_factory):
    page = open_page(browser_factory(), live_server)

    registrations = page.evaluate(
        "() => navigator.serviceWorker.getRegistrations().then((entries) => entries.length)"
    )
    assert registrations >= 1

    page.reload(wait_until="networkidle")

    expect(page.locator("[data-landing-bucket='create']")).to_have_attribute(
        "aria-expanded", "false"
    )
    expect(page.locator("[data-landing-bucket='join']")).to_have_attribute("aria-expanded", "false")
    expect(page.locator("#open-rules-menu")).to_be_visible()


def test_hidden_card_reveal_is_public_and_forces_take_pile(live_server, browser_factory):
    host_page = open_page(browser_factory(), live_server)
    create_table(host_page, "Host")
    invite_code = extract_invite_code(host_page)

    guest_page = open_page(browser_factory(), live_server)
    join_table(guest_page, invite_code, "Guest")

    host_page.locator("#start-game").click()
    choose_public_cards(host_page)
    choose_public_cards(guest_page)
    wait_until_public_selection_finished(host_page)
    wait_until_public_selection_finished(guest_page)

    session = session_manager.get_session(invite_code)
    game = session.game_manager.game
    game.deck = PileOfCards()
    game.play_pile = PileOfCards([Card(9, Suit.HEART)])
    game.valid_ranks = {10, 11, 12}
    host_player = game.get_player(0)
    guest_player = game.get_player(1)
    host_player.private_cards = SetOfCards()
    host_player.public_cards = SetOfCards()
    host_player.hidden_cards = SetOfCards([Card(4, Suit.CLOVERS)])
    guest_player.private_cards = SetOfCards([Card(12, Suit.HEART)])
    guest_player.public_cards = SetOfCards()
    session.apply_action(
        session.get_player_by_seat(0).token, ActionRequest(type="play_hidden_card")
    )

    host_page.reload(wait_until="networkidle")
    guest_page.reload(wait_until="networkidle")

    expect(host_page.locator(".dock-prompt")).to_contain_text("Take the pile")
    expect(host_page.locator(".pile-preview")).to_contain_text("4")
    expect(guest_page.locator(".pile-preview")).to_contain_text("4")
