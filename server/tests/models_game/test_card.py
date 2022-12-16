import dataclasses

import pytest

from pyshithead.models.game import Card, SpecialRank, Suit


def test_card_initialization_class():
    card = Card(rank=2, suit=Suit.TILES)
    assert card.rank == 2
    assert card.suit == Suit.TILES


def test_card_initialization_dict():
    card = Card(**{"rank": 2, "suit": Suit.TILES})
    assert card.rank == 2
    assert card.suit == Suit.TILES


def test_card_to_dict(card_2h):
    assert card_2h.dict() == {"rank": 2, "suit": Suit.HEART}


def test_card_immutability(card_2h: Card):
    with pytest.raises(TypeError):
        card_2h.rank = 3
    with pytest.raises(TypeError):
        card_2h.suit = Suit.HEART


def test_card_comparison(card_2h, card_2t):
    assert card_2h == Card(rank=2, suit=Suit.HEART)
    assert card_2h != card_2t
    assert card_2h == card_2h
