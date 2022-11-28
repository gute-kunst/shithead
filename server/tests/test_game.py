from pyshithead import NBR_HIDDEN_CARDS, NBR_TOTAL_CARDS, Game, Player


def test_game_players(two_players):
    game = Game(two_players)
    assert len(game.active_players) == 2
