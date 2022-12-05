import pytest

from pyshithead import (
    NBR_HIDDEN_CARDS,
    NBR_TOTAL_CARDS,
    Game,
    NextPlayerEvent,
    Player,
    PrivateCardsRequest,
    SetOfCards,
    TakePlayPileRequest,
)
from pyshithead.errors import *


def test_game_players(game_with_two_players_start: Game, valid_all):
    game = game_with_two_players_start
    assert len(game.active_players) == 2
    assert game.valid_ranks == valid_all
    assert len(game.deck) == NBR_TOTAL_CARDS - (NBR_HIDDEN_CARDS * 6)


def test_game_take_playpile_while_empty(game_with_two_players_empty_playpile: Game):
    game = game_with_two_players_empty_playpile
    with pytest.raises(TakePlayPileNotAllowed):
        req = TakePlayPileRequest(game.get_player())
        game.process_playrequest(req)


def test_game_take_playpile_while_should_play_hidden(game_with_two_players_empty_playpile: Game):
    game = game_with_two_players_empty_playpile
    game.get_player().private_cards.take_all()
    game.deck.take_all()
    game.play_pile.put(game.get_player().public_cards.take_all())
    req = TakePlayPileRequest(game.get_player())
    with pytest.raises(TakePlayPileNotAllowed):
        game.process_playrequest(req)


def test_game_next_player(game_with_two_players_start: Game):
    game = game_with_two_players_start
    current_player = game.get_player()
    game.next_player_event = NextPlayerEvent.NEXT_2
    game.update_next_player()
    assert game.get_player() == current_player


def test_game_game_over(game_last_move: Game):
    p1: Player = game_last_move.get_player()
    req = PrivateCardsRequest(p1, [p1.private_cards.return_single()])
    with pytest.raises(SystemExit):
        game_last_move.process_playrequest(req)
