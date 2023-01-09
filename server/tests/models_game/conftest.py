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


@pytest.fixture
def card_2t():
    return Card(2, Suit.TILES)


@pytest.fixture
def card_2h():
    return Card(2, Suit.HEART)


@pytest.fixture
def card_2c():
    return Card(2, Suit.CLOVERS)


@pytest.fixture
def card_2p():
    return Card(2, Suit.PIKES)


@pytest.fixture
def card_3h():
    return Card(3, Suit.HEART)


@pytest.fixture
def card_3t():
    return Card(3, Suit.TILES)


@pytest.fixture
def card_3p():
    return Card(3, Suit.PIKES)


@pytest.fixture
def card_invisible_p():
    return Card(SpecialRank.INVISIBLE, Suit.PIKES)


@pytest.fixture
def four_cards_same_rank(card_2c, card_2t, card_2h, card_2p):
    return [card_2c, card_2t, card_2h, card_2p]


@pytest.fixture
def four_cards_same_rank_with_invisible_middle(four_cards_same_rank: list):
    four_cards_same_rank.insert(2, Card(SpecialRank.INVISIBLE, Suit.PIKES))
    return four_cards_same_rank


@pytest.fixture
def four_cards_same_rank_with_invisible_everywhere(four_cards_same_rank: list):
    four_cards_same_rank.insert(1, Card(SpecialRank.INVISIBLE, Suit.PIKES))
    four_cards_same_rank.insert(3, Card(SpecialRank.INVISIBLE, Suit.PIKES))
    four_cards_same_rank.insert(5, Card(SpecialRank.INVISIBLE, Suit.PIKES))
    return four_cards_same_rank


@pytest.fixture
def four_cards_same_rank_with_invisible_end(four_cards_same_rank: list):
    four_cards_same_rank.append(Card(SpecialRank.INVISIBLE, Suit.PIKES))
    return four_cards_same_rank


@pytest.fixture
def four_cards_same_rank_with_interseption(four_cards_same_rank: list, card_3t):
    four_cards_same_rank.insert(2, card_3t)
    return four_cards_same_rank


@pytest.fixture
def three_cards_same_rank_with_invisible_end(four_cards_same_rank: list):
    four_cards_same_rank[3] = Card(SpecialRank.INVISIBLE, Suit.PIKES)
    return four_cards_same_rank


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
def two_cards_high_low():
    return [Card(SpecialRank.HIGHLOW, Suit.HEART), Card(SpecialRank.HIGHLOW, Suit.TILES)]


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
def two_cards_diff_rank_and_diff_tile(card_2t, card_3h):
    return [card_2t, card_3h]


@pytest.fixture
def two_cards(card_2t, card_2h):
    return [card_2t, card_2h]


@pytest.fixture
def two_other_cards(card_3t, card_3h):
    return [card_3t, card_3h]


@pytest.fixture
def three_cards(card_2t, card_2h, card_2c):
    return [card_2t, card_2h, card_2c]


@pytest.fixture
def three_other_cards(card_2p, card_3h, card_3t):
    return [card_2p, card_3h, card_3t]


@pytest.fixture
def three_more_other_cards():
    return [Card(4, Suit.PIKES), Card(4, Suit.HEART), Card(4, Suit.CLOVERS)]


@pytest.fixture
def two_cards_identical(card_2t):
    return [card_2t, card_2t]


@pytest.fixture
def two_cards_equal_rank(card_2t, card_2h):
    return [card_2t, card_2h]


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
def player_with_6_private_cards(player: Player, three_cards, three_other_cards):
    player.private_cards.cards.update(three_cards + three_other_cards)
    return player


@pytest.fixture
def player_with_3_hidden_and_3_public_cards(player: Player, three_cards, three_other_cards):
    player.hidden_cards.cards.update(three_cards)
    player.public_cards.cards.update(three_other_cards)
    return player


@pytest.fixture
def player_initialized(player: Player):
    deck = Dealer.provide_deck()
    Dealer.deal_cards_to_players(deck, [player], put_public_to_private=False)
    return player


@pytest.fixture
def game_with_two_players_start(two_players):
    return Game.initialize(two_players)


@pytest.fixture
def game_with_two_players_during_game_empty_playpile(two_players):
    deck = Dealer.provide_deck()
    Dealer.deal_cards_to_players(deck, two_players, put_public_to_private=False)
    return Game(two_players, deck, state=GameState.DURING_GAME)


@pytest.fixture
def game_last_move(two_players, card_2h):
    deck = Dealer.provide_deck()
    Dealer.deal_cards_to_players(deck, two_players, put_public_to_private=False)
    two_players[0].public_cards.cards.clear()
    two_players[0].private_cards = SetOfCards([card_2h])
    two_players[0].hidden_cards.cards.clear()
    return Game(two_players, PileOfCards(), state=GameState.DURING_GAME)


@pytest.fixture
def game_hidden_move(two_players, card_2h):
    deck = Dealer.provide_deck()
    Dealer.deal_cards_to_players(deck, two_players, put_public_to_private=False)
    two_players[0].public_cards.cards.clear()
    two_players[0].private_cards.cards.clear()
    two_players[0].hidden_cards = SetOfCards([card_2h])
    return Game(two_players, PileOfCards(), state=GameState.DURING_GAME)


@pytest.fixture
def game_player_wins(three_players):
    deck = Dealer.provide_deck()
    Dealer.deal_cards_to_players(deck, three_players[1:], put_public_to_private=False)
    three_players[0].public_cards.cards.clear()
    three_players[0].hidden_cards.cards.clear()
    return Game(three_players, PileOfCards(), state=GameState.DURING_GAME)
