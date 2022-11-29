from pyshithead import PileOfCards


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


def test_pileofcards_four_of_same_rank_from_top_true(four_cards_same_rank):
    pile = PileOfCards(four_cards_same_rank)
    assert pile.four_of_same_rank_from_top() is True


def test_pileofcards_four_of_same_rank_from_top_empty():
    pile = PileOfCards()
    assert pile.four_of_same_rank_from_top() is False


def test_pileofcards_four_of_same_rank_from_top_including_invisible(
    four_cards_same_rank: list, card_invisible_p
):
    four_cards_same_rank.insert(1, card_invisible_p)
    pile = PileOfCards(four_cards_same_rank)
    assert pile.four_of_same_rank_from_top() is True


def test_pileofcards_four_of_same_rank_from_top_including_1_wrong(
    four_cards_same_rank: list, card_3t
):
    four_cards_same_rank.insert(1, card_3t)
    pile = PileOfCards(four_cards_same_rank)
    assert pile.four_of_same_rank_from_top() is False


def test_pileofcards_four_of_same_rank_from_top_3x_with_invisible(
    four_cards_same_rank: list, card_invisible_p
):
    four_cards_same_rank[1] = card_invisible_p
    pile = PileOfCards(four_cards_same_rank)
    assert pile.four_of_same_rank_from_top() is False


def test_pileofcards_four_of_same_rank_from_top_4x_invisible(four_cards_invisible: list):
    pile = PileOfCards(four_cards_invisible)
    assert pile.four_of_same_rank_from_top() is True
