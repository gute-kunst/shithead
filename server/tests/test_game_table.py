import pytest

from pyshithead.models.web import GameTable


@pytest.mark.skip(reason="later")
def test_game_table_connect():
    gt = GameTable(game=None, game_id=1)
