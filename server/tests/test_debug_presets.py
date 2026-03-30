import pytest
from fastapi.testclient import TestClient

from pyshithead.debug_presets import DEBUG_PRESET_NAMES, seed_debug_preset
from pyshithead.debug_server import create_debug_app
from pyshithead.main import app, create_app
from pyshithead.models.game import JOKER_RANK, SpecialRank
from pyshithead.models.session import GameSessionManager


@pytest.mark.parametrize("preset_name", DEBUG_PRESET_NAMES)
def test_debug_preset_builds_consistent_session(preset_name: str):
    manager = GameSessionManager()
    seed = seed_debug_preset(manager, preset_name)

    snapshot = seed.session.build_snapshot()
    private_states = [seed.session.build_private_state(seat.seat) for seat in seed.seats]

    assert seed.session.invite_code in manager.sessions
    assert len(seed.seats) >= 2
    assert snapshot.invite_code == seed.session.invite_code
    assert all(
        private_state.seat in {seat.seat for seat in seed.seats} for private_state in private_states
    )


def test_hidden_take_preset_exposes_forced_take_state():
    manager = GameSessionManager()
    seed = seed_debug_preset(manager, "hidden-take")

    snapshot = seed.session.build_snapshot()
    private_state = seed.session.build_private_state(0)

    assert snapshot.game_state == "DURING_GAME"
    assert snapshot.play_pile[0].rank == 4
    assert private_state.pending_hidden_take is True
    assert snapshot.status_message == "Host revealed 4 and must take the pile."


def test_revealed_card_presets_keep_resolution_state_visible():
    manager = GameSessionManager()

    joker_seed = seed_debug_preset(manager, "revealed-joker")
    joker_snapshot = joker_seed.session.build_snapshot()
    joker_private_state = joker_seed.session.build_private_state(0)
    assert joker_snapshot.pending_joker_selection is True
    assert joker_private_state.pending_joker_card.rank == JOKER_RANK

    seven_seed = seed_debug_preset(manager, "revealed-seven")
    seven_snapshot = seven_seed.session.build_snapshot()
    seven_private_state = seven_seed.session.build_private_state(0)
    assert seven_snapshot.pending_joker_selection is True
    assert seven_private_state.pending_joker_card.rank == SpecialRank.HIGHLOW


def test_game_over_preset_marks_finished_positions():
    manager = GameSessionManager()
    seed = seed_debug_preset(manager, "game-over")

    snapshot = seed.session.build_snapshot()

    assert snapshot.status == "GAME_OVER"
    assert any(player.finished_position == 1 for player in snapshot.players)


def test_debug_bootstrap_route_exists_only_on_debug_app():
    debug_app, seed = create_debug_app("choose-public")
    normal_app = create_app(session_manager=GameSessionManager())
    player = seed.session.get_player_by_seat(0)

    with TestClient(debug_app, base_url="http://localhost") as client:
        response = client.get(
            f"/debug/session?invite={seed.session.invite_code}&token={player.token}"
        )
        assert response.status_code == 200
        assert "shithead.alpha.session" in response.text
        assert player.token in response.text
        assert 'id="app" class="app-root"' in response.text
        assert "/static/app.js" in response.text

    with TestClient(normal_app, base_url="http://localhost") as client:
        response = client.get("/debug/session?invite=DEBUG&token=missing")
        assert response.status_code == 404

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/debug/session?invite=DEBUG&token=missing")
        assert response.status_code == 404
