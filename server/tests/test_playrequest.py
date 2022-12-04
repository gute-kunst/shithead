import pytest
from pytest_lazyfixture import lazy_fixture

from pyshithead import (
    BurnEvent,
    Card,
    Choice,
    ChoosePublicCardsRequest,
    NextPlayerEvent,
    Player,
    PrivateCardsRequest,
    RankEvent,
    RankType,
    SetOfCards,
    SpecialRank,
    TakePlayPileRequest,
)
from pyshithead.errors import *


def test_privatecardsrequest_cards_on_players_hands_false(player: Player, two_cards_equal_rank):
    with pytest.raises(CardsNotInPlayersPrivateHandsError):
        PrivateCardsRequest(player, two_cards_equal_rank)


def test_privatecardsrequest_ranks_are_equal_false(
    player: Player, two_cards_diff_rank_and_diff_tile
):
    player.private_cards = SetOfCards(two_cards_diff_rank_and_diff_tile)
    with pytest.raises(CardsRequestRanksNotEqualError):
        PrivateCardsRequest(player, two_cards_diff_rank_and_diff_tile)


def test_privatecardsrequest_high_low_consistency_1(player: Player, card_high_low_h: Card):
    player.private_cards = SetOfCards([card_high_low_h])
    with pytest.raises(CardsRequestHighLowCardWithoutChoiceError):
        PrivateCardsRequest(player, [card_high_low_h])


def test_privatecardsrequest_high_low_consistency_2(player: Player, card_2h: Card):
    player.private_cards = SetOfCards([card_2h])
    with pytest.raises(CardsRequestHighLowChoiceWithoutHighLowCardError):
        PrivateCardsRequest(player, [card_2h], Choice.HIGHER)


@pytest.mark.parametrize("choice", [Choice.LOWER, Choice.HIGHER])
def test_privatecardsrequest_consistent_choice(player: Player, card_high_low_h, choice):
    player.private_cards = SetOfCards([card_high_low_h])
    try:
        PrivateCardsRequest(player, [card_high_low_h], choice)
    except PyshitheadError as error:
        assert False, error.message


def test_choosepubliccardsrequest_correct_number_was_chosen(
    player_with_6_private_cards, three_cards
):
    try:
        ChoosePublicCardsRequest(player_with_6_private_cards, three_cards)
    except WrongNumberOfChosencardsError:
        assert False


def test_choosepubliccardsrequest_wrong_number_was_chosen(player_with_6_private_cards: Player):
    with pytest.raises(WrongNumberOfChosencardsError):
        ChoosePublicCardsRequest(
            player_with_6_private_cards, [player_with_6_private_cards.private_cards.return_single()]
        )


@pytest.mark.parametrize(
    "card, choice, rank_event",
    [
        (lazy_fixture("card_3t"), None, RankEvent(RankType.TOPRANK, 3)),
        (
            lazy_fixture("card_high_low_h"),
            Choice.HIGHER,
            RankEvent(RankType.HIGHER, SpecialRank.HIGHLOW),
        ),
        (
            lazy_fixture("card_invisible"),
            None,
            RankEvent(RankType.KEEPCURRENT, SpecialRank.INVISIBLE),
        ),
        (
            lazy_fixture("card_2h"),
            None,
            RankEvent(RankType.TOPRANK, SpecialRank.RESET),
        ),
        (
            lazy_fixture("card_burn"),
            None,
            RankEvent(RankType.TOPRANK, SpecialRank.RESET),
        ),
    ],
)
def test_cardsrequest_rank(player, card, choice, rank_event):
    req = PrivateCardsRequest(player, [card], choice, consistency_check=False)
    assert req.get_rank_event() == rank_event


def test_cardsrequest_next_player(player, card_2t):
    req = PrivateCardsRequest(player, [card_2t], consistency_check=False)
    assert req.get_next_player_event() == NextPlayerEvent.NEXT


def test_cardsrequest_next_player_skip(player, four_skip_cards):
    req = PrivateCardsRequest(player, four_skip_cards[:1], consistency_check=False)
    assert req.get_next_player_event() == NextPlayerEvent.NEXT_2
    req2 = PrivateCardsRequest(player, four_skip_cards[:2], consistency_check=False)
    assert req2.get_next_player_event() == NextPlayerEvent.NEXT_3
    req3 = PrivateCardsRequest(player, four_skip_cards[:3], consistency_check=False)
    assert req3.get_next_player_event() == NextPlayerEvent.NEXT_4


def test_cardsrequest_next_player_burn(player, card_burn):
    req = PrivateCardsRequest(player, [card_burn], consistency_check=False)
    assert req.get_next_player_event() == NextPlayerEvent.SAME


def test_cardsrequest_burn(player, card_2h, card_burn):
    req = PrivateCardsRequest(player, [card_2h], consistency_check=False)
    assert req.get_burn_event() == BurnEvent.NO
    req2 = PrivateCardsRequest(player, [card_burn], consistency_check=False)
    assert req2.get_burn_event() == BurnEvent.YES


def test_choosepubliccardsrequest_process(player_with_6_private_cards: Player):
    p = player_with_6_private_cards
    p_chosen_cards = [card for card in p.private_cards][:3]
    try:
        req = ChoosePublicCardsRequest(
            player_with_6_private_cards, p_chosen_cards, consistency_check=True
        )
    except WrongNumberOfChosencardsError:
        assert False
    req.process()
    assert len(p.private_cards) == 3
    assert len(p.public_cards) == 3
    assert p.public_cards.isdisjoint(p.private_cards) is True
    assert p.public_cards == SetOfCards(p_chosen_cards)


def test_takeplaypile_consistency(player: Player, card_3h):
    player.private_cards.put([card_3h])
    try:
        TakePlayPileRequest(player)
    except PyshitheadError:
        assert False
