import pytest

from pyshithead.models.game import (
    Card,
    Dealer,
    Game,
    GameState,
    PileOfCards,
    Player,
    SetOfCards,
    SpecialRank,
    Suit,
)


def _card_2t():
    return Card(2, Suit.TILES)


@pytest.fixture
def card_2t():
    return _card_2t()


def _card_2h():
    return Card(2, Suit.HEART)


@pytest.fixture
def card_2h():
    return _card_2h()


def _card_3h():
    return Card(3, Suit.HEART)


@pytest.fixture
def card_3h():
    return _card_3h()


def _card_3t():
    return Card(3, Suit.TILES)


@pytest.fixture
def card_3t():
    return _card_3t()


def _card_3p():
    return Card(3, Suit.PIKES)


@pytest.fixture
def card_3p():
    return _card_3p()


def _card_2c():
    return Card(2, Suit.CLOVERS)


def _card_2p():
    return Card(2, Suit.PIKES)


@pytest.fixture
def card_invisible_p():
    return Card(SpecialRank.INVISIBLE, Suit.PIKES)


@pytest.fixture
def four_cards_same_rank():
    return [_card_2c(), _card_2t(), _card_2h(), _card_2p()]


@pytest.fixture
def four_cards_same_rank_with_invisible_middle():
    return [_card_2c(), _card_2t(), Card(SpecialRank.INVISIBLE, Suit.PIKES), _card_2h(), _card_2p()]


@pytest.fixture
def four_cards_same_rank_with_invisible_everywhere():
    return [
        _card_2c(),
        Card(SpecialRank.INVISIBLE, Suit.PIKES),
        _card_2t(),
        Card(SpecialRank.INVISIBLE, Suit.PIKES),
        _card_2h(),
        Card(SpecialRank.INVISIBLE, Suit.PIKES),
        _card_2p(),
    ]


@pytest.fixture
def four_cards_same_rank_with_invisible_end():
    return [_card_2c(), _card_2t(), _card_2h(), _card_2p(), Card(SpecialRank.INVISIBLE, Suit.PIKES)]


@pytest.fixture
def four_cards_same_rank_with_interseption():
    return [_card_2c(), _card_2t(), _card_3t(), _card_2h(), _card_2p()]


@pytest.fixture
def three_cards_same_rank_with_invisible_end():
    return [_card_2c(), _card_2t(), _card_2h(), Card(SpecialRank.INVISIBLE, Suit.PIKES)]


@pytest.fixture
def four_skip_cards():
    return [
        Card(SpecialRank.SKIP, Suit.HEART),
        Card(SpecialRank.SKIP, Suit.TILES),
        Card(SpecialRank.SKIP, Suit.CLOVERS),
        Card(SpecialRank.SKIP, Suit.PIKES),
    ]


@pytest.fixture
def card_high_low_h():
    return Card(SpecialRank.HIGHLOW, Suit.HEART)


@pytest.fixture
def card_invisible():
    return Card(SpecialRank.INVISIBLE, Suit.HEART)


@pytest.fixture
def card_burn():
    return Card(SpecialRank.BURN, Suit.HEART)


@pytest.fixture
def card_reset():
    return Card(SpecialRank.RESET, Suit.HEART)


@pytest.fixture
def card_skip():
    return Card(SpecialRank.SKIP, Suit.HEART)


@pytest.fixture
def four_cards_invisible():
    return [
        Card(SpecialRank.INVISIBLE, Suit.PIKES),
        Card(SpecialRank.INVISIBLE, Suit.HEART),
        Card(SpecialRank.INVISIBLE, Suit.CLOVERS),
        Card(SpecialRank.INVISIBLE, Suit.TILES),
    ]


@pytest.fixture
def two_cards_diff_rank_and_diff_tile():
    return [_card_2t(), _card_3h()]


@pytest.fixture
def two_cards():
    return [_card_2t(), _card_2h()]


@pytest.fixture
def two_other_cards():
    return [_card_3t(), _card_3h()]


def _three_cards():
    return [_card_2t(), _card_2h(), _card_2c()]


@pytest.fixture
def three_cards():
    return _three_cards()


def _three_other_cards():
    return [_card_2p(), _card_3h(), _card_3t()]


@pytest.fixture
def three_other_cards():
    return _three_other_cards()


@pytest.fixture
def three_more_other_cards():
    return [Card(4, Suit.PIKES), Card(4, Suit.HEART), Card(4, Suit.CLOVERS)]


@pytest.fixture
def two_cards_identical():
    return [_card_2t(), _card_2t()]


@pytest.fixture
def two_cards_equal_rank():
    return [_card_2t(), _card_2h()]


@pytest.fixture
def two_players():
    return [Player(1), Player(2)]


@pytest.fixture
def player():
    return Player(1)


@pytest.fixture
def three_players():
    return [Player(1), Player(2), Player(3)]


@pytest.fixture
def valid_all():
    return set([2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])


@pytest.fixture
def valid_higher():
    return set([7, 8, 9, 10, 11, 12, 13, 14])


@pytest.fixture
def valid_lower():
    return set([2, 3, 4, 5, 6, 7])


@pytest.fixture
def valid_14():
    return set([SpecialRank.RESET, SpecialRank.INVISIBLE, SpecialRank.BURN, 14])


@pytest.fixture
def player_with_6_private_cards():
    player = Player(1)
    player.private_cards.cards.update(_three_cards() + _three_other_cards())
    return player


@pytest.fixture
def player_with_3_hidden_and_3_public_cards():
    player = Player(1)
    player.hidden_cards.cards.update(_three_cards())
    player.public_cards.cards.update(_three_other_cards())
    return player


@pytest.fixture
def player_initialized():
    player = Player(1)
    deck = Dealer.provide_deck()
    Dealer.deal_cards_to_players(deck, [player], put_public_to_private=False)
    return player


@pytest.fixture
def game_with_two_players_start():
    return Game.initialize([Player(1), Player(2)])


@pytest.fixture
def game_with_two_players_during_game_empty_playpile():
    players = [Player(1), Player(2)]
    deck = Dealer.provide_deck()
    Dealer.deal_cards_to_players(deck, players, put_public_to_private=False)
    return Game(players, deck, state=GameState.DURING_GAME)


@pytest.fixture
def game_last_move():
    p1 = Player(1)
    p2 = Player(2)
    deck = Dealer.provide_deck()
    Dealer.deal_cards_to_players(deck, [p1, p2], put_public_to_private=False)
    p1.public_cards.cards.clear()
    p1.private_cards = SetOfCards([_card_2h()])
    p1.hidden_cards.cards.clear()
    return Game([p1, p2], PileOfCards(), state=GameState.DURING_GAME)


@pytest.fixture
def game_hidden_move():
    p1 = Player(1)
    p2 = Player(2)
    deck = Dealer.provide_deck()
    Dealer.deal_cards_to_players(deck, [p1, p2], put_public_to_private=False)
    p1.public_cards.cards.clear()
    p1.private_cards.cards.clear()
    p1.hidden_cards = SetOfCards([_card_2h()])
    return Game([p1, p2], PileOfCards(), state=GameState.DURING_GAME)


@pytest.fixture
def game_player_wins():
    players = [Player(1), Player(2), Player(3)]
    deck = Dealer.provide_deck()
    Dealer.deal_cards_to_players(deck, players[1:], put_public_to_private=False)
    players[0].public_cards.cards.clear()
    players[0].hidden_cards.cards.clear()
    return Game(players, PileOfCards(), state=GameState.DURING_GAME)
