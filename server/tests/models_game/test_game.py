import pytest
from pytest_lazyfixture import lazy_fixture

from pyshithead.models.game import (
    NBR_HIDDEN_CARDS,
    NBR_TOTAL_CARDS,
    Card,
    ChoosePublicCardsRequest,
    Game,
    GameState,
    HiddenCardRequest,
    Player,
    PrivateCardsRequest,
    SetOfCards,
    Suit,
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
    with pytest.raises(TakePlayPileNotAllowedError):
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
    with pytest.raises(TakePlayPileNotAllowedError):
        game.process_playrequest(req)


def test_game_first_private_card(game_with_two_players_during_game_empty_playpile: Game):
    game = game_with_two_players_during_game_empty_playpile
    player = game.get_player()
    card = Card(5, Suit.TILES)
    req = PrivateCardsRequest(player, [card])
    game.process_playrequest(req)
    assert card in game.play_pile.cards
    assert game.active_players.get_ordered_list() == [Player(2), Player(1)]


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
        (lazy_fixture("card_2h"), [Player(2), Player(3)]),
        (lazy_fixture("card_skip"), [Player(3), Player(2)]),
        (lazy_fixture("card_burn"), [Player(2), Player(3)]),
        (lazy_fixture("four_skip_cards"), [Player(2), Player(3)]),
        (lazy_fixture("four_cards_invisible"), [Player(2), Player(3)]),
    ],
)
def test_game_player_wins(game_player_wins: Game, last_cards: list[Card], play_order):
    cards = last_cards if isinstance(last_cards, list) else [last_cards]

    players: list[Player] = game_player_wins.active_players.get_ordered_list()
    players[0].private_cards = SetOfCards(cards)
    req = PrivateCardsRequest(players[0], cards)
    game_player_wins.process_playrequest(req)
    assert game_player_wins.state == GameState.DURING_GAME
    assert game_player_wins.ranking == [players[0]]
    assert game_player_wins.active_players.get_ordered_list() == play_order


def test_game_last_player_chose_cards(game_with_two_players_start: Game):
    game = game_with_two_players_start
    players: list[Player] = game.active_players.get_ordered_list()
    req0 = ChoosePublicCardsRequest(players[0], list(players[0].private_cards.cards)[:3])
    game.process_choose_cards(req0)
    assert game.state == GameState.PLAYERS_CHOOSE_PUBLIC_CARDS
    req1 = ChoosePublicCardsRequest(players[1], list(players[1].private_cards.cards)[:3])
    game.process_choose_cards(req1)
    assert game.state == GameState.DURING_GAME


def test_game_hidden_move(game_hidden_move: Game):
    players: list[Player] = game_hidden_move.active_players.get_ordered_list()
    req = HiddenCardRequest(players[0])
    assert req.cards in game_hidden_move.get_player().hidden_cards
    game_hidden_move.process_hidden_card(req)
    assert game_hidden_move.state == GameState.DURING_GAME
    assert game_hidden_move.active_players.get_ordered_list() == players
    assert req.cards in game_hidden_move.get_player().private_cards
    assert game_hidden_move.state is GameState.DURING_GAME


@pytest.mark.skip(reason="mock example")
def test_game_mocked(game_with_two_players_during_game_empty_playpile: Game, mocker):
    game = game_with_two_players_during_game_empty_playpile
    assert game.game_id == 1
    mocker.patch.object(game, "game_id", 2)
    assert game.game_id == 2
