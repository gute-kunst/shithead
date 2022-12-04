import pytest

from pyshithead import (
    NBR_HIDDEN_CARDS,
    NBR_TOTAL_CARDS,
    Game,
    Player,
    PrivateCardsRequest,
    SetOfCards,
    TakePlayPileRequest,
)


def test_game_players(game_with_two_players_start: Game, valid_all):
    game = game_with_two_players_start
    assert len(game.active_players) == 2
    assert game.valid_ranks == valid_all
    assert len(game.deck) == NBR_TOTAL_CARDS - (NBR_HIDDEN_CARDS * 6)


@pytest.mark.skip(reason="later")
def test_game_process_playrequest(game_with_two_players_empty_playpile: Game):
    game = game_with_two_players_empty_playpile
    incomming_player_id = game.active_players.head.data.id_
    player = game.get_player(incomming_player_id)
    incomming_cards = list(player.private_cards.cards)[0]
    req = PrivateCardsRequest(player, [incomming_cards])
    game.process_playrequest(req)
    set2 = SetOfCards(game.play_pile.cards)
    set1 = SetOfCards([incomming_cards])
    assert (set1 in set2) is True
    assert game.active_players.head.data.id_ != incomming_player_id
    print("done")


def test_game_take_playpile_while_empty(game_with_two_players_empty_playpile: Game):
    game = game_with_two_players_empty_playpile
    with pytest.raises(ValueError):
        req = TakePlayPileRequest(game.get_player())
        game.process_playrequest(req)


def test_game_take_playpile_while_should_play_hidden(game_with_two_players_empty_playpile: Game):
    game = game_with_two_players_empty_playpile
    game.get_player().private_cards.take_all()
    game.play_pile.put(game.get_player().public_cards.take_all())
    with pytest.raises(ValueError):
        req = TakePlayPileRequest(game.get_player())
        game.process_playrequest(req)
