import dataclasses

import pytest

from pyshithead import Card, Suit


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
