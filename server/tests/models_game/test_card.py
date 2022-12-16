import dataclasses
import json

import pytest

from pyshithead.models.game import Card, SpecialRank, Suit


def test_card_initialization():
    card = Card(2, Suit.TILES)
    assert card.rank == 2
    assert card.suit == Suit.TILES


def test_card_initialization_from_dict(card_2h):
    card_dict = dict({"rank": 2, "suit": int(Suit.HEART)})
    card = Card(**card_dict)
    assert card == card_2h


def test_card_immutability(card_2h):
    with pytest.raises(dataclasses.FrozenInstanceError):
        card_2h.rank = 3
    with pytest.raises(dataclasses.FrozenInstanceError):
        card_2h.Suite = Suit.HEART


def test_card_comparison(card_2h, card_2t):
    assert card_2h == Card(2, Suit.HEART)
    assert card_2h != card_2t
    assert card_2h == card_2h
    assert Card(2, Suit.HEART) == Card(SpecialRank.RESET, Suit.HEART)


def test_card_json_dumps(card_2h):
    j = json.dumps(vars(card_2h))
    assert json.dumps({"rank": 2, "suit": Suit.HEART}) == j
