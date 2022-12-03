import pytest

from pyshithead import (
    NBR_HIDDEN_CARDS,
    NBR_TOTAL_CARDS,
    CircularDoublyLinkedList,
    Dealer,
    PileOfCards,
    Player,
    SetOfCards,
)


def test_dealer_provide_shuffled_deck_has_no_duplicates():
    deck = Dealer.provide_shuffled_deck()
    assert len(deck) == NBR_TOTAL_CARDS
    cardset = SetOfCards(deck.cards)
    assert len(cardset) == NBR_TOTAL_CARDS  # sets cannot contain duplicates


@pytest.mark.skip(reason="later")
def test_dealer_provide_shuffled_deck_is_random():
    pass


def test_dealer_deal_cards_to_players(two_players: list[Player]):
    player_list = CircularDoublyLinkedList(two_players)
    deck = Dealer.provide_shuffled_deck()
    Dealer.deal_cards_to_players(deck, player_list)
    assert len(player_list.head.data.hidden_cards) == NBR_HIDDEN_CARDS
    assert len(player_list.head.data.private_cards) == NBR_HIDDEN_CARDS * 2
    assert len(player_list.head.next.data.hidden_cards) == NBR_HIDDEN_CARDS
    assert len(player_list.head.next.data.private_cards) == NBR_HIDDEN_CARDS * 2
    assert len(deck) == NBR_TOTAL_CARDS - (NBR_HIDDEN_CARDS * 6)


def test_dealer_fillup_cards_in_game(player: Player):
    deck = Dealer.provide_shuffled_deck()
    Dealer.fillup_cards(deck, player)
    assert len(player.private_cards) == 3

    Dealer.fillup_cards(deck, player)
    assert len(player.private_cards) == 3

    player.private_cards.put(deck.take_from_top(1))
    Dealer.fillup_cards(deck, player)
    assert len(player.private_cards) == 4


def test_dealer_fillup_cards_empty_deck(player_with_3_hidden_and_3_public_cards: Player):
    player = player_with_3_hidden_and_3_public_cards
    public_cards_before = SetOfCards(player.public_cards.cards)
    hidden_cards_before = SetOfCards(player.hidden_cards.cards)
    deck = PileOfCards()
    Dealer.fillup_cards(deck, player)
    assert player.private_cards == public_cards_before
    assert player.hidden_cards == hidden_cards_before
    assert len(deck) == 0


def test_dealer_fillup_cards_single_card_in_deck(
    player_with_3_hidden_and_3_public_cards: Player, card_3p
):
    player = player_with_3_hidden_and_3_public_cards
    hidden_cards_before = SetOfCards(player.hidden_cards.cards)
    deck = PileOfCards([card_3p])
    Dealer.fillup_cards(deck, player)
    assert player.private_cards == SetOfCards([card_3p])
    assert len(player.private_cards) == 1
    assert player.hidden_cards == hidden_cards_before
    assert len(deck) == 0
