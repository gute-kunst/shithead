from gameplay import TOTAL_NBR_OF_CARDS, Game, Player, SetOfCards


def test_game_initialization(two_players):
    pass


def test_game_deal_cards_check_amount(two_players: list[Player]):
    game = Game(two_players)
    game.deal_cards()
    assert len(two_players[0].hidden_cards) == 3
    assert len(two_players[1].hidden_cards) == 3
    assert len(two_players[0].private_cards) == 6
    assert len(two_players[1].private_cards) == 6


def test_game_deal_cards_check_value(two_players: list[Player]):
    game = Game(two_players)
