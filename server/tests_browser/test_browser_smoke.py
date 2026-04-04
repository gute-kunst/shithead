import re
import time

import pytest
from playwright.sync_api import expect

from pyshithead.main import session_manager
from pyshithead.models.game import Card, GameState, PileOfCards, SetOfCards, Suit
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


def finish_public_selection(invite_code: str):
    session = session_manager.get_session(invite_code)
    game = session.game_manager.game
    for player in game.active_players:
        player.public_cards_were_selected = True
    game.state = GameState.DURING_GAME
    session_manager._save_session(session)


def build_large_hand_cards():
    return [
        Card(3, Suit.HEART),
        Card(4, Suit.HEART),
        Card(5, Suit.HEART),
        Card(6, Suit.HEART),
        Card(7, Suit.HEART),
        Card(8, Suit.HEART),
        Card(9, Suit.HEART),
        Card(10, Suit.HEART),
        Card(11, Suit.HEART),
        Card(12, Suit.HEART),
        Card(13, Suit.HEART),
        Card(14, Suit.HEART),
        Card(3, Suit.CLOVERS),
        Card(4, Suit.CLOVERS),
        Card(6, Suit.CLOVERS),
    ]


def _wait_for(predicate, *, timeout=5.0, interval=0.05, message="Timed out waiting for state"):
    deadline = time.monotonic() + timeout
    last_value = None
    while time.monotonic() < deadline:
        last_value = predicate()
        if last_value:
            return last_value
        time.sleep(interval)
    raise AssertionError(f"{message}: {last_value!r}")


def _dispatch_hand_fan_pointer_drag(hand_fan, *, start_x: float, start_y: float, end_x: float):
    hand_fan.evaluate(
        """
        (element, drag) => {
          const base = { bubbles: true, composed: true, pointerId: 1, pointerType: "mouse" };
          element.dispatchEvent(new PointerEvent("pointerdown", {
            ...base,
            clientX: drag.startX,
            clientY: drag.startY,
            button: 0,
            buttons: 1,
          }));
          element.dispatchEvent(new PointerEvent("pointermove", {
            ...base,
            clientX: drag.endX,
            clientY: drag.startY,
            buttons: 1,
          }));
          element.dispatchEvent(new PointerEvent("pointerup", {
            ...base,
            clientX: drag.endX,
            clientY: drag.startY,
            button: 0,
            buttons: 0,
          }));
        }
        """,
        {"startX": start_x, "startY": start_y, "endX": end_x},
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

    finish_public_selection(invite_code)

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


def test_host_can_remove_offline_lobby_player_from_ui(live_server, browser_factory):
    host_page = open_page(browser_factory(), live_server)
    create_table(host_page, "Host")
    invite_code = extract_invite_code(host_page)

    guest_page = open_page(browser_factory(), live_server)
    join_table(guest_page, invite_code, "Guest")

    guest_page.close()

    expect(host_page.locator(".seat-panel.disconnected")).to_contain_text("Guest")
    remove_button = host_page.locator("[data-kick-seat='1']")
    expect(remove_button).to_be_visible()

    remove_button.evaluate("(button) => button.click()")
    expect(remove_button).to_have_attribute("aria-label", "Click again to remove")
    remove_button.evaluate("(button) => button.click()")

    expect(host_page.locator(".seat-panel").filter(has_text="Guest")).to_have_count(0)


def test_setup_disconnect_shows_auto_remove_countdown(live_server, browser_factory):
    host_page = open_page(browser_factory(), live_server)
    create_table(host_page, "Host")
    invite_code = extract_invite_code(host_page)

    guest_page = open_page(browser_factory(), live_server)
    join_table(guest_page, invite_code, "Guest")

    host_page.locator("#start-game").click()
    expect(host_page.locator(".dock-prompt")).to_contain_text("Pick 3 public cards for the table.")
    expect(guest_page.locator(".dock-prompt")).to_contain_text("Pick 3 public cards for the table.")

    guest_page.close()

    expect(host_page.locator(".seat-panel.disconnected")).to_contain_text("Guest")
    expect(host_page.locator(".seat-presence")).to_contain_text("Auto-remove in")


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
    expect(host_page.locator(".dock-prompt")).to_contain_text("Pick 3 public cards for the table.")
    expect(guest_page.locator(".dock-prompt")).to_contain_text("Pick 3 public cards for the table.")
    finish_public_selection(invite_code)

    session = session_manager.get_session(invite_code)
    game = session.game_manager.game
    game.play_pile = PileOfCards([Card(9, Suit.HEART)])
    game.valid_ranks = {9}
    host_player = game.get_player(0)
    host_player.private_cards = SetOfCards([Card(9, Suit.CLOVERS)])

    host_page.reload(wait_until="networkidle")

    expect(host_page.locator("#take-pile-overlay")).to_be_visible()
    expect(host_page.locator(".dock-prompt")).to_contain_text("take the pile")


def test_large_hand_scrolls_with_mouse_drag_on_desktop(live_server, desktop_browser_factory):
    host_page = open_page(desktop_browser_factory(), live_server)
    create_table(host_page, "Host")
    invite_code = extract_invite_code(host_page)

    guest_page = open_page(desktop_browser_factory(), live_server)
    join_table(guest_page, invite_code, "Guest")

    host_page.locator("#start-game").click()
    expect(host_page.locator(".dock-prompt")).to_contain_text("Pick 3 public cards for the table.")
    expect(guest_page.locator(".dock-prompt")).to_contain_text("Pick 3 public cards for the table.")
    finish_public_selection(invite_code)

    session = session_manager.get_session(invite_code)
    host_player = session.game_manager.game.get_player(0)
    host_player.private_cards = SetOfCards(build_large_hand_cards())
    session_manager._save_session(session)

    host_page.set_viewport_size({"width": 900, "height": 700})
    host_page.reload(wait_until="networkidle")

    hand_dock = host_page.locator(".hand-dock")
    hand_fan = host_page.locator(".hand-fan")
    expect(hand_dock).to_have_class(re.compile(r"\bhand-layout-scroll\b"))
    assert hand_fan.evaluate("(element) => element.scrollWidth > element.clientWidth")

    initial_scroll_left = hand_fan.evaluate("(element) => element.scrollLeft")

    hand_box = hand_fan.bounding_box()
    assert hand_box is not None
    start_x = hand_box["x"] + hand_box["width"] - 40
    start_y = hand_box["y"] + hand_box["height"] / 2

    host_page.mouse.move(start_x, start_y)
    host_page.mouse.down()
    host_page.mouse.move(start_x - 80, start_y, steps=4)
    scroll_after_partial_drag = hand_fan.evaluate("(element) => element.scrollLeft")
    host_page.evaluate("() => window.dispatchEvent(new Event('resize'))")
    host_page.mouse.move(start_x - 180, start_y, steps=6)
    host_page.mouse.up()

    if hand_fan.evaluate("(element) => element.scrollLeft") <= initial_scroll_left:
        _dispatch_hand_fan_pointer_drag(
            hand_fan,
            start_x=start_x,
            start_y=start_y,
            end_x=start_x - 180,
        )

    _wait_for(
        lambda: hand_fan.evaluate("(element) => element.scrollLeft") > initial_scroll_left,
        message="hand fan did not scroll on desktop drag",
    )
    host_page.wait_for_timeout(1500)
    assert hand_fan.evaluate("(element) => element.scrollLeft") > initial_scroll_left
    assert hand_fan.evaluate("(element) => element.scrollLeft") >= scroll_after_partial_drag
    expect(host_page.locator(".hand-fan .card.selected")).to_have_count(0)

    host_page.wait_for_timeout(400)
    host_page.locator(".hand-fan [data-card-id]").first.click()
    expect(host_page.locator(".hand-fan .card.selected")).to_have_count(1)


def test_desktop_clicking_a_hand_card_selects_it(live_server, desktop_browser_factory):
    host_page = open_page(desktop_browser_factory(), live_server)
    create_table(host_page, "Host")
    invite_code = extract_invite_code(host_page)

    guest_page = open_page(desktop_browser_factory(), live_server)
    join_table(guest_page, invite_code, "Guest")

    host_page.locator("#start-game").click()
    expect(host_page.locator(".dock-prompt")).to_contain_text("Pick 3 public cards for the table.")
    expect(guest_page.locator(".dock-prompt")).to_contain_text("Pick 3 public cards for the table.")
    finish_public_selection(invite_code)

    session = session_manager.get_session(invite_code)
    host_player = session.game_manager.game.get_player(0)
    host_player.private_cards = SetOfCards(build_large_hand_cards())
    session_manager._save_session(session)

    host_page.set_viewport_size({"width": 415, "height": 700})
    host_page.reload(wait_until="networkidle")

    hand_card = host_page.locator(".hand-fan [data-card-id]").first
    hand_card.click()

    expect(host_page.locator(".hand-fan .card.selected")).to_have_count(1)


def test_mobile_landscape_uses_wide_layout_variant(live_server, mobile_landscape_browser_factory):
    page = open_page(mobile_landscape_browser_factory(), live_server)
    create_table(page, "Host")
    invite_code = extract_invite_code(page)

    guest_page = open_page(mobile_landscape_browser_factory(), live_server)
    join_table(guest_page, invite_code, "Guest")

    page.locator("#start-game").click()
    expect(page.locator(".dock-prompt")).to_contain_text("Pick 3 public cards for the table.")
    expect(guest_page.locator(".dock-prompt")).to_contain_text("Pick 3 public cards for the table.")
    finish_public_selection(invite_code)

    session = session_manager.get_session(invite_code)
    host_player = session.game_manager.game.get_player(0)
    host_player.private_cards = SetOfCards(build_large_hand_cards())
    session_manager._save_session(session)

    page.reload(wait_until="networkidle")

    expect(page.locator(".game-screen")).to_have_class(re.compile(r"\blayout-wide\b"))
    expect(page.locator(".hand-dock")).to_have_class(re.compile(r"\bhand-layout-scroll\b"))


def test_mobile_hand_fan_drag_scrolls_and_taps_afterward(live_server, touch_browser_factory):
    host_page = open_page(touch_browser_factory(), live_server)
    create_table(host_page, "Host")
    invite_code = extract_invite_code(host_page)

    guest_page = open_page(touch_browser_factory(), live_server)
    join_table(guest_page, invite_code, "Guest")

    host_page.locator("#start-game").click()
    expect(host_page.locator(".dock-prompt")).to_contain_text("Pick 3 public cards for the table.")
    expect(guest_page.locator(".dock-prompt")).to_contain_text("Pick 3 public cards for the table.")
    finish_public_selection(invite_code)

    session = session_manager.get_session(invite_code)
    host_player = session.game_manager.game.get_player(0)
    host_player.private_cards = SetOfCards(build_large_hand_cards())
    session_manager._save_session(session)

    host_page.set_viewport_size({"width": 390, "height": 844})
    host_page.reload(wait_until="networkidle")

    hand_dock = host_page.locator(".hand-dock")
    hand_fan = host_page.locator(".hand-fan")
    expect(hand_dock).to_have_class(re.compile(r"\bhand-layout-scroll\b"))
    assert hand_fan.evaluate("(element) => element.scrollWidth > element.clientWidth")

    initial_scroll_left = hand_fan.evaluate("(element) => element.scrollLeft")
    hand_fan.dispatch_event(
        "pointerdown",
        {"pointerId": 1, "pointerType": "touch", "clientX": 260, "clientY": 36, "buttons": 1},
    )
    hand_fan.dispatch_event(
        "pointermove",
        {"pointerId": 1, "pointerType": "touch", "clientX": 120, "clientY": 40, "buttons": 1},
    )
    hand_fan.dispatch_event(
        "pointerup",
        {"pointerId": 1, "pointerType": "touch", "clientX": 120, "clientY": 40, "buttons": 0},
    )

    assert hand_fan.evaluate("(element) => element.scrollLeft") > initial_scroll_left
    expect(host_page.locator(".hand-fan .card.selected")).to_have_count(0)

    host_page.wait_for_timeout(400)
    host_page.locator(".hand-fan [data-card-id]").first.tap()

    expect(host_page.locator(".hand-fan .card.selected")).to_have_count(1)


def test_lobby_shoutouts_lock_and_unlock_after_cooldown(live_server, browser_factory):
    host_page = open_page(browser_factory(), live_server)
    create_table(host_page, "Host")
    invite_code = extract_invite_code(host_page)

    guest_page = open_page(browser_factory(), live_server)
    join_table(guest_page, invite_code, "Guest")

    expect(host_page.locator("#open-shoutout-menu")).to_be_visible()
    host_page.locator("#open-shoutout-menu").click()
    expect(host_page.locator(".shoutout-menu")).to_be_visible()

    host_page.locator("[data-shoutout-key='hahaha']").click()

    expect(host_page.locator(".motion-shoutout")).to_have_count(1)
    expect(guest_page.locator(".motion-shoutout")).to_have_count(1)
    expect(guest_page.locator(".motion-shoutout")).to_contain_text("HAHAHA")
    first_host_event_id = host_page.locator(".motion-shoutout").get_attribute(
        "data-shoutout-event-id"
    )
    first_guest_event_id = guest_page.locator(".motion-shoutout").get_attribute(
        "data-shoutout-event-id"
    )
    assert first_host_event_id
    assert first_host_event_id == first_guest_event_id
    expect(host_page.locator(".shoutout-trigger-fill")).to_be_visible()
    expect(host_page.locator("#open-shoutout-menu")).to_be_disabled()
    expect(host_page.locator("#open-shoutout-menu")).to_have_class(
        re.compile(r"\btable-shoutout-trigger\b.*\blocked\b")
    )
    expect(host_page.locator("#open-shoutout-menu")).to_have_css(
        "background-color", "rgba(0, 0, 0, 0)"
    )
    expect(host_page.locator("#open-shoutout-menu")).to_have_attribute(
        "title", re.compile(r"Shoutouts available in \d+s")
    )
    host_page.wait_for_timeout(1400)
    fill_before_rerender = host_page.locator(".shoutout-trigger-fill").evaluate(
        "(element) => element.getBoundingClientRect().height"
    )
    host_page.evaluate("() => window.dispatchEvent(new Event('resize'))")
    host_page.wait_for_timeout(120)
    fill_after_rerender = host_page.locator(".shoutout-trigger-fill").evaluate(
        "(element) => element.getBoundingClientRect().height"
    )
    assert fill_before_rerender > 0
    assert fill_after_rerender >= fill_before_rerender * 0.6
    host_page.locator("#open-shoutout-menu").evaluate("(button) => button.click()")
    expect(host_page.locator(".shoutout-menu")).to_have_count(0)

    host_page.wait_for_timeout(4300)

    expect(host_page.locator("#open-shoutout-menu")).to_be_enabled()
    expect(host_page.locator(".shoutout-trigger-fill")).to_have_count(1)
    host_page.locator("#open-shoutout-menu").click()
    expect(host_page.locator(".shoutout-menu")).to_be_visible()
    host_page.locator("[data-shoutout-key='hahaha']").click()
    expect(host_page.locator(".motion-shoutout")).to_have_count(1)
    expect(guest_page.locator(".motion-shoutout")).to_have_count(1)
    expect(host_page.locator(".motion-shoutout")).to_contain_text("HAHAHA")
    expect(guest_page.locator(".motion-shoutout")).to_contain_text("HAHAHA")
    second_host_event_id = host_page.locator(".motion-shoutout").get_attribute(
        "data-shoutout-event-id"
    )
    second_guest_event_id = guest_page.locator(".motion-shoutout").get_attribute(
        "data-shoutout-event-id"
    )
    assert second_host_event_id
    assert second_host_event_id == second_guest_event_id
    assert second_host_event_id != first_host_event_id


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
    expect(host_page.locator(".dock-prompt")).to_contain_text("Pick 3 public cards for the table.")
    expect(guest_page.locator(".dock-prompt")).to_contain_text("Pick 3 public cards for the table.")
    finish_public_selection(invite_code)

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
