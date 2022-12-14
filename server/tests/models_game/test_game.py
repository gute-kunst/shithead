import pytest
from pytest_lazyfixture import lazy_fixture

from pyshithead.models.game import (
    NBR_HIDDEN_CARDS,
    NBR_TOTAL_CARDS,
    Card,
    Game,
    GameState,
    HiddenCardRequest,
    NextPlayerEvent,
    Player,
    PrivateCardsRequest,
    SetOfCards,
    TakePlayPileRequest,
)
from pyshithead.models.game.errors import *


def test_game_players(game_with_two_players_start: Game, valid_all):
    game = game_with_two_players_start
    assert len(game.active_players) == 2
    assert game.valid_ranks == valid_all
    assert len(game.deck) == NBR_TOTAL_CARDS - (NBR_HIDDEN_CARDS * 6)


def test_game_take_playpile_while_empty(game_with_two_players_during_game_empty_playpile: Game):
    game = game_with_two_players_during_game_empty_playpile
    with pytest.raises(TakePlayPileNotAllowed):
        req = TakePlayPileRequest(game.get_player())
        game.process_playrequest(req)


def test_game_take_playpile_while_should_play_hidden(
    game_with_two_players_during_game_empty_playpile: Game,
):
    game = game_with_two_players_during_game_empty_playpile
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
    p2: Player = game_last_move.active_players.head.next.data
    req = PrivateCardsRequest(p1, [p1.private_cards.return_single()])
    game_last_move.process_playrequest(req)
    assert game_last_move.state == GameState.GAME_OVER
    assert game_last_move.ranking == [p1, p2]


@pytest.mark.parametrize(
    "last_cards, play_order",
    [
        (lazy_fixture("card_2h"), [Player(id_=2), Player(id_=3)]),
        (lazy_fixture("card_skip"), [Player(id_=3), Player(id_=2)]),
        (lazy_fixture("card_burn"), [Player(id_=2), Player(id_=3)]),
        (lazy_fixture("four_skip_cards"), [Player(id_=2), Player(id_=3)]),
        (lazy_fixture("four_cards_invisible"), [Player(id_=2), Player(id_=3)]),
    ],
)
def test_game_player_wins(game_player_wins: Game, last_cards: list[Card] | Card, play_order):
    cards = last_cards if isinstance(last_cards, list) else [last_cards]

    players: list[Player] = game_player_wins.active_players.get_ordered_list()
    players[0].private_cards = SetOfCards(cards=cards)
    req = PrivateCardsRequest(players[0], cards)
    game_player_wins.process_playrequest(req)
    assert game_player_wins.state == GameState.DURING_GAME
    assert game_player_wins.ranking == [players[0]]
    assert game_player_wins.active_players.get_ordered_list() == play_order


def test_game_hidden_move(game_hidden_move: Game):
    players: list[Player] = game_hidden_move.active_players.get_ordered_list()
    req = HiddenCardRequest(players[0])
    assert req.cards in game_hidden_move.get_player().hidden_cards
    game_hidden_move.process_playrequest(req)
    assert game_hidden_move.state == GameState.DURING_GAME
    assert game_hidden_move.active_players.get_ordered_list() == players
    assert req.cards in game_hidden_move.get_player().private_cards
    assert game_hidden_move.state is GameState.DURING_GAME
