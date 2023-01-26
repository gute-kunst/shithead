import dataclasses

import pytest

from pyshithead.models.game import Card, SpecialRank, Suit


def test_card_immutability(card_2h: Card):
    with pytest.raises(dataclasses.FrozenInstanceError):
        card_2h.rank = 3  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        card_2h.suit = Suit.HEART  # type: ignore[misc]


def test_card_comparison(card_2h: Card, card_2t: Card):
    assert card_2h == Card(2, Suit.HEART)
    assert card_2h != card_2t
    assert card_2h == card_2h
    assert Card(2, Suit.HEART) == Card(SpecialRank.RESET, Suit.HEART)
