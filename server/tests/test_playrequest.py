from pyshithead import ChoosePublicCardsRequest, Player, SetOfCards


def test_choosepubliccardsrequest_process(player_with_6_private_cards: Player):
    p = player_with_6_private_cards
    p_chosen_cards = [card for card in p.private_cards][:3]
    req = ChoosePublicCardsRequest(player_with_6_private_cards, p_chosen_cards)
    req.process()
    assert len(p.private_cards) == 3
    assert len(p.public_cards) == 3
    assert p.public_cards.isdisjoint(p.private_cards) is True
    assert p.public_cards == SetOfCards(p_chosen_cards)
