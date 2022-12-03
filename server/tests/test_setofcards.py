import pytest

from pyshithead import SetOfCards


def test_setofcards_empty_initialize():
    cardset = SetOfCards()
    assert cardset.is_empty() == True


def test_setofcards_initialize_multiple_sets(card_2t, two_cards, card_2h):
    cardset1 = SetOfCards([card_2t])
    cardset2 = SetOfCards(two_cards)
    assert len(cardset1) == 1
    assert len(cardset2) == 2
    cardset1.put([card_2h])
    assert len(cardset1) == 2
    assert len(cardset2) == 2


def test_setofcards_rank_is_equal_true(two_cards_equal_rank):
    cardset = SetOfCards(two_cards_equal_rank)
    assert cardset.rank_is_equal() is True


def test_setofcards_rank_is_equal_false(two_cards_diff_rank_and_diff_tile):
    cardset = SetOfCards(two_cards_diff_rank_and_diff_tile)
    assert cardset.rank_is_equal() is False


def test_setofcards_ensure_no_duplicates(two_cards_identical):
    cardset = SetOfCards(two_cards_identical)
    assert len(cardset) == 1


def test_setofcards_put_list(two_cards, two_other_cards):
    cardset = SetOfCards(two_cards)
    cardset.put(two_other_cards)
    assert len(cardset) == 4


def test_setofcards_put_set(two_cards, two_other_cards):
    cardset = SetOfCards(two_cards)
    cardset.put(set(two_other_cards))
    assert len(cardset) == 4


def test_setofcards_in_true(two_cards, two_other_cards):
    cardset1 = SetOfCards(two_cards + two_other_cards)
    cardset2 = SetOfCards(two_cards)
    assert (cardset2 in cardset1) is True


def test_setofcards_in_false(two_cards, two_other_cards):
    cardset1 = SetOfCards(two_cards)
    cardset2 = SetOfCards(two_other_cards)
    assert (cardset2 in cardset1) is False


def test_setofcards_iterate(two_cards):
    cardset = SetOfCards(two_cards)
    for i, card in enumerate(cardset):
        assert card in two_cards
    assert i == 1


def test_setofcards_get_ranks_different(card_2t, card_3t):
    cardset = SetOfCards([card_2t, card_3t])
    assert sorted(cardset.get_ranks()) == sorted([2, 3])


def test_setofcards_get_ranks_same(card_2t, card_2h):
    cardset = SetOfCards([card_2t, card_2h])
    assert sorted(cardset.get_ranks()) == sorted([2, 2])


def test_setofcards_take_invalid_card(card_2t, card_2h):
    cardset = SetOfCards([card_2t])
    with pytest.raises(ValueError):
        cardset.take({card_2h})


def test_setofcards_take_single(card_2t, card_2h):
    cardset = SetOfCards([card_2t, card_2h])
    token_card = cardset.take(set([card_2h]))
    assert token_card == set([card_2h])
    assert cardset == SetOfCards([card_2t])
    assert len(cardset) == 1


def test_setofcards_take_multiple(two_cards, two_other_cards):
    cardset = SetOfCards(two_cards + two_other_cards)
    token_cards = cardset.take(set(two_other_cards))
    assert token_cards == set(two_other_cards)
    assert cardset == SetOfCards(two_cards)
    assert len(cardset) == 2


def test_setofcards_take_all(two_cards):
    cardset = SetOfCards(two_cards)
    token_cards = cardset.take_all()
    assert len(cardset) == 0
    assert token_cards == set(two_cards)


def test_setofcards_isdisjoint(card_2h, card_2t):
    cardset1 = SetOfCards([card_2h])
    cardset2 = SetOfCards([card_2t])
    assert cardset1.isdisjoint(cardset2) is True
    cardset1.put([card_2t])
    assert cardset1.isdisjoint(cardset2) is False
