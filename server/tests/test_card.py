import dataclasses

import pytest

from pyshithead import Card, RankEvent, RankType, SpecialRank, Suit


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


def test_card_initialization():
    card = Card(2, Suit.TILES)
    assert card.rank == 2
    assert card.suit == Suit.TILES


def test_card_immutability(card_2h):
    with pytest.raises(dataclasses.FrozenInstanceError):
        card_2h.rank = 3
    with pytest.raises(dataclasses.FrozenInstanceError):
        card_2h.Suite = Suit.HEART


def test_card_comparison(card_2h, card_2t):
    assert card_2h == Card(2, Suit.HEART)
    assert card_2h != card_2t
    assert card_2h == card_2h


def test_rankevent_get_all_valid_ranks(valid_all):
    rank_event = RankEvent(RankType.TOPRANK, top_rank=2)
    assert valid_all == rank_event.get_valid_ranks()


def test_rankevent_get_valid_ranks_higher(valid_higher):
    rank_event = RankEvent(RankType.HIGHER, top_rank=7)
    assert valid_higher == rank_event.get_valid_ranks()


def test_rankevent_get_valid_ranks_lower(valid_lower):
    rank_event = RankEvent(RankType.LOWER, top_rank=7)
    assert valid_lower == rank_event.get_valid_ranks()


def test_rankevent_get_valid_ranks_14(valid_14):
    rank_event = RankEvent(RankType.TOPRANK, top_rank=14)
    assert valid_14 == rank_event.get_valid_ranks()


def test_rankevent_get_valid_ranks_invisible_on_14(valid_14):
    rank_event = RankEvent(RankType.TOPRANK, top_rank=14)
    valid = rank_event.get_valid_ranks()
    rank_event_invisible = RankEvent(RankType.KEEPCURRENT, top_rank=SpecialRank.INVISIBLE)
    assert valid_14 == rank_event_invisible.get_valid_ranks(valid)


def test_rankevent_get_valid_ranks_invisible_on_lower(valid_lower):
    rank_event = RankEvent(RankType.LOWER, top_rank=7)
    valid = rank_event.get_valid_ranks()
    rank_event_invisible = RankEvent(RankType.KEEPCURRENT, top_rank=SpecialRank.INVISIBLE)
    assert valid_lower == rank_event_invisible.get_valid_ranks(valid)
