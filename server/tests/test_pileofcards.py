from gameplay import TOTAL_NBR_OF_CARDS, PileOfCards, SetOfCards


def test_pileofcards_take(card_2t, card_3h):
    top_of_pile = card_2t
    bottom_of_pile = card_3h
    pile = PileOfCards([top_of_pile, bottom_of_pile])
    returned_cards = pile.take(1)
    assert top_of_pile == returned_cards[0]
    assert len(returned_cards) == 1
    assert len(pile) == 1


def test_pileofcards_takeall(two_cards):
    pile = PileOfCards(two_cards)
    returned_cards = pile.take_all()
    assert len(returned_cards) == 2
    assert pile.is_empty() == True


def test_pileofcards_generate_deck_has_no_duplicates():
    deck = PileOfCards.generate_deck()
    assert len(deck) == TOTAL_NBR_OF_CARDS
    cardset = SetOfCards(deck.cards)
    assert len(cardset) == TOTAL_NBR_OF_CARDS  # sets cannot contain duplicates


# def test_pileofcards_generate_deck_random_ceck


#
