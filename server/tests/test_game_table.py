from pyshithead.models.web import Client, GameTable


def test_game_table_connect():
    gt = GameTable(game=None, game_id=1)
