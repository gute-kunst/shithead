import pytest

from pyshithead import Card, Player, Suit


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
def four_cards_same_rank():
    return [_card_2c, _card_2t, _card_2h, _card_2p]


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
