import pytest

from pyshithead import Card, ChoosePublicCardsRequest, Game, Player, SpecialRank, Suit


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
    player.private_cards.cards.update(
        [_card_2c(), _card_2t(), _card_2h(), _card_2p(), _card_3t(), _card_3h()]
    )
    return player


@pytest.fixture
def game_with_two_players_start():
    return Game([Player(1), Player(2)])


@pytest.fixture
def game_with_two_players_during_game():
    game = Game([Player(1), Player(2)])
    for player in game.active_players.traverse_single():
        req = ChoosePublicCardsRequest(
            player.data, [card for card in player.data.private_cards][:3]
        )
        req.process()
    return game
