import pytest

from pyshithead import NBR_TOTAL_CARDS, PileOfCards, SetOfCards


def test_pileofcards_take(card_2t, card_3h):
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


@pytest.mark.skip(reason="function not working")
def test_pileofcards_get_pile_event(four_cards_same_rank):
    pile = PileOfCards(four_cards_same_rank)
    # pile.get_pile_events()
