import pytest

from pyshithead import NBR_HIDDEN_CARDS, NBR_TOTAL_CARDS, ChoosePublicCardsRequest, Game, Player


@pytest.mark.skip(reason="high level test not working")
def test_game_players(valid_all):
    p1 = Player(1)
    p2 = Player(2)
    game = Game([p1, p2])
    assert len(game.active_players) == 2
    assert game.valid_ranks == valid_all
    assert len(game.deck) == NBR_TOTAL_CARDS - (NBR_HIDDEN_CARDS * 6)
    p1_chosen_cards = [card for card in game.get_player(p1.id_).private_cards][:3]
    req = ChoosePublicCardsRequest(p1, p1_chosen_cards)
    # game.process_playrequest()
    print("done")
