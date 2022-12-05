import pytest
from pytest_lazyfixture import lazy_fixture

from pyshithead import PileOfCards


def test_pileofcards_take_from_top(card_2t, card_3h):
    top_of_pile = card_2t
    bottom_of_pile = card_3h
    pile = PileOfCards([top_of_pile, bottom_of_pile])
    returned_cards = pile.take_from_top(1)
    assert top_of_pile == returned_cards[0]
    assert len(returned_cards) == 1
    assert len(pile) == 1
    assert bottom_of_pile == pile.cards[0]


def test_pileofcards_takeall(two_cards):
    pile = PileOfCards(two_cards)
    returned_cards = pile.take_all()
    assert len(returned_cards) == 2
    assert pile.is_empty() == True


def test_pileofcards_put_single(two_cards, card_3h):
    pile = PileOfCards(two_cards)
    pile.put([card_3h])
    assert len(pile) == 3
    assert pile[0] == card_3h


def test_pileofcards_put_list(two_cards, two_other_cards):
    pile = PileOfCards(two_cards)
    pile.put(two_other_cards)
    assert len(pile) == 4
    assert pile[0] == two_other_cards[0]
    assert pile[1] == two_other_cards[1]


def test_pileofcards_put_set(two_cards, two_other_cards):
    pile = PileOfCards(two_cards)
    pile.put(set(two_other_cards))
    assert len(pile) == 4


@pytest.mark.parametrize(
    "cards, expected_value",
    [
        ([], False),
        (lazy_fixture("four_cards_same_rank_with_interseption"), False),
        (lazy_fixture("three_cards_same_rank_with_invisible_end"), False),
        (lazy_fixture("four_cards_invisible"), True),
        (lazy_fixture("four_cards_same_rank"), True),
        (lazy_fixture("four_skip_cards"), True),
        (lazy_fixture("four_cards_same_rank_with_invisible_middle"), True),
        (lazy_fixture("four_cards_same_rank_with_invisible_end"), True),
        (lazy_fixture("four_cards_same_rank_with_invisible_everywhere"), True),
    ],
)
def test_pileofcards_four_of_same_rank_from_top(cards, expected_value):
    pile = PileOfCards(cards)
    assert pile.has_four_times_same_rank_from_top() is expected_value


def test_pileofcards_look_from_top(four_cards_same_rank):
    pile = PileOfCards(four_cards_same_rank)
    top_two_card = [four_cards_same_rank[0], four_cards_same_rank[1]]
    looked_up_cards = pile.look_from_top(2)
    assert looked_up_cards == top_two_card
    assert len(pile) == 4
