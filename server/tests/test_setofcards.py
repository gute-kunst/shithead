from gameplay import SetOfCards


def test_setofcards_empty_initialize():
    cardset = SetOfCards()
    assert cardset.is_empty() == True


def test_setofcards_initialize_multiple_sets(card_2t, two_cards, card_2h):
    cardset1 = SetOfCards([card_2t])
    cardset2 = SetOfCards(two_cards)
    assert len(cardset1) == 1
    assert len(cardset2) == 2
    cardset1.add([card_2h])
    assert len(cardset1) == 2
    assert len(cardset2) == 2


def test_setofcards_rank_is_equal_true(two_cards_equal_rank):
    cardset = SetOfCards(two_cards_equal_rank)
    assert cardset.rank_is_equal() == True


def test_setofcards_rank_is_equal_false(two_cards_different_rank_and_different_tile):
    cardset = SetOfCards(two_cards_different_rank_and_different_tile)
    assert cardset.rank_is_equal() == False


def test_setofcards_ensure_no_duplicates(two_cards_identical):
    cardset = SetOfCards(two_cards_identical)
    assert len(cardset) == 1


def test_setofcards_add_list(two_cards, two_other_cards):
    cardset = SetOfCards(two_cards)
    cardset.add(two_other_cards)
    assert len(cardset) == 4


def test_setofcards_add_set(two_cards, two_other_cards):
    cardset = SetOfCards(two_cards)
    cardset.add(set(two_other_cards))
    assert len(cardset) == 4
