from pyshithead.models.game import (
    ALL_RANKS,
    BurnEvent,
    PileOfCards,
    RankEvent,
    RankType,
    SpecialRank,
)


def test_rankevent_get_all_valid_ranks():
    rank_event = RankEvent(RankType.TOPRANK, top_rank=2)
    assert set(ALL_RANKS) == rank_event.get_valid_ranks(set(ALL_RANKS))


def test_rankevent_get_valid_ranks_higher(valid_higher):
    rank_event = RankEvent(RankType.HIGHER, top_rank=7)
    assert valid_higher == rank_event.get_valid_ranks(set(ALL_RANKS))


def test_rankevent_get_valid_ranks_lower(valid_lower):
    rank_event = RankEvent(RankType.LOWER, top_rank=7)
    assert valid_lower == rank_event.get_valid_ranks(set(ALL_RANKS))


def test_rankevent_get_valid_ranks_14(valid_14):
    rank_event = RankEvent(RankType.TOPRANK, top_rank=14)
    assert valid_14 == rank_event.get_valid_ranks(set(ALL_RANKS))


def test_rankevent_get_valid_ranks_invisible_on_14(valid_14):
    rank_event = RankEvent(RankType.TOPRANK, top_rank=14)
    valid = rank_event.get_valid_ranks(set(ALL_RANKS))
    rank_event_invisible = RankEvent(RankType.KEEPCURRENT, top_rank=SpecialRank.INVISIBLE)
    assert valid_14 == rank_event_invisible.get_valid_ranks(valid)


def test_rankevent_get_valid_ranks_invisible_on_lower(valid_lower):
    rank_event = RankEvent(RankType.LOWER, top_rank=7)
    valid = rank_event.get_valid_ranks(set(ALL_RANKS))
    rank_event_invisible = RankEvent(RankType.KEEPCURRENT, top_rank=SpecialRank.INVISIBLE)
    assert valid_lower == rank_event_invisible.get_valid_ranks(valid)


def test_rankevent_get_valid_ranks_invisible_on_empty(valid_all):
    rank_event_invisible = RankEvent(RankType.KEEPCURRENT, top_rank=SpecialRank.INVISIBLE)
    assert valid_all == rank_event_invisible.get_valid_ranks(valid_all)


def test_burn_event_process(card_2h):
    play_pile = PileOfCards([card_2h])
    event = BurnEvent.YES
    event.process(play_pile)
    assert play_pile.is_empty()
