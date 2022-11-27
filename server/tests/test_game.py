from gameplay import NBR_HIDDEN_CARDS, TOTAL_NBR_OF_CARDS, Game, Player


def test_game_players(two_players):
    game = Game(two_players)
    assert len(game.active_players) == 2


def test_game_deal_cards_amount(two_players: list[Player]):
    game = Game(two_players)
    assert len(game.active_players.head.data.hidden_cards) == NBR_HIDDEN_CARDS
    assert len(game.active_players.head.data.private_cards) == NBR_HIDDEN_CARDS * 2
    assert len(game.active_players.head.next.data.hidden_cards) == NBR_HIDDEN_CARDS
    assert len(game.active_players.head.next.data.private_cards) == NBR_HIDDEN_CARDS * 2
    assert len(game.deck) == TOTAL_NBR_OF_CARDS - (NBR_HIDDEN_CARDS * 6) - 1
    assert len(game.play_pile) == 1
