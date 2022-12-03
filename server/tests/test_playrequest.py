import pytest

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
)


def test_privatecardsrequest_cards_on_players_hands_false(player: Player, two_cards_equal_rank):
    req = PrivateCardsRequest(player, two_cards_equal_rank, consistency_check=False)
    assert req.cards_on_players_hands() is False
    assert req.is_consistent() is False


def test_privatecardsrequest_ranks_are_equal_false(
    player: Player, two_cards_diff_rank_and_diff_tile
):
    player.private_cards = SetOfCards(two_cards_diff_rank_and_diff_tile)
    req = PrivateCardsRequest(player, two_cards_diff_rank_and_diff_tile, consistency_check=False)
    assert req.ranks_are_equal() is False
    assert req.is_consistent() is False


def test_privatecardsrequest_high_low_consistency_1(player: Player, card_high_low_h: Card):
    player.private_cards = SetOfCards([card_high_low_h])
    req = PrivateCardsRequest(player, [card_high_low_h], consistency_check=False)
    assert req.high_low_consistency() is False
    assert req.is_consistent() is False


def test_privatecardsrequest_high_low_consistency(player: Player, card_2h: Card):
    player.private_cards = SetOfCards([card_2h])
    req = PrivateCardsRequest(player, [card_2h], Choice.HIGHER, consistency_check=False)
    assert req.high_low_consistency() is False
    assert req.is_consistent() is False


def test_privatecardsrequest_consistent_high_choice(player: Player, card_high_low_h):
    player.private_cards = SetOfCards([card_high_low_h])
    req = PrivateCardsRequest(player, [card_high_low_h], Choice.HIGHER, consistency_check=False)
    assert req.high_low_consistency() is True
    assert req.is_consistent() is True


def test_privatecardsrequest_consistent_low_choice(player: Player, card_high_low_h):
    player.private_cards = SetOfCards([card_high_low_h])
    req = PrivateCardsRequest(player, [card_high_low_h], Choice.LOWER, consistency_check=False)
    assert req.high_low_consistency() is True
    assert req.is_consistent() is True


def test_choosepubliccardsrequest_correct_number_was_chosen(player, three_cards, two_cards):
    req = ChoosePublicCardsRequest(player, three_cards, consistency_check=False)
    assert req.correct_number_was_chosen() is True
    req2 = ChoosePublicCardsRequest(player, two_cards, consistency_check=False)
    assert req2.correct_number_was_chosen() is False


def test_cardsrequest_rank_toprank(player, card_3t):
    req = PrivateCardsRequest(player, [card_3t], consistency_check=False)
    assert req.get_rank_event() == RankEvent(RankType.TOPRANK, 3)


def test_cardsrequest_rank_highlow(player, card_high_low_h: Card):
    req = PrivateCardsRequest(player, [card_high_low_h], Choice.HIGHER, consistency_check=False)
    assert req.get_rank_event() == RankEvent(RankType.HIGHER, card_high_low_h.rank)


def test_cardsrequest_rank_invisible(player, card_invisible: Card):
    req = PrivateCardsRequest(player, [card_invisible], consistency_check=False)
    assert req.get_rank_event() == RankEvent(RankType.KEEPCURRENT, card_invisible.rank)


def test_cardsrequest_rank_reset(player, card_2h: Card):
    req = PrivateCardsRequest(player, [card_2h], consistency_check=False)
    assert req.get_rank_event() == RankEvent(RankType.TOPRANK, card_2h.rank)


def test_cardsrequest_rank_burn(player, card_burn: Card):
    req = PrivateCardsRequest(player, [card_burn], consistency_check=False)
    assert req.get_rank_event() == RankEvent(RankType.TOPRANK, 2)


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
    req = ChoosePublicCardsRequest(
        player_with_6_private_cards, p_chosen_cards, consistency_check=True
    )
    assert req.is_consistent() is True
    req.process()
    assert len(p.private_cards) == 3
    assert len(p.public_cards) == 3
    assert p.public_cards.isdisjoint(p.private_cards) is True
    assert p.public_cards == SetOfCards(p_chosen_cards)


def test_choosepubliccardsrequest_consistency_check(player: Player, card_2t: Card):
    with pytest.raises(ValueError):
        ChoosePublicCardsRequest(player, [card_2t], consistency_check=True)


def test_cardrequest_consistency_check(player: Player, card_2t: Card):
    with pytest.raises(ValueError):
        PrivateCardsRequest(player, [card_2t], consistency_check=True)
