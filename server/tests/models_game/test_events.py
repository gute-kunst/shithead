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
    assert rank_event.get_valid_ranks(set(ALL_RANKS)) == set(ALL_RANKS)


def test_rankevent_get_valid_ranks_higher(valid_higher):
    rank_event = RankEvent(RankType.HIGHER, top_rank=7)
    assert rank_event.get_valid_ranks(set(ALL_RANKS)) == valid_higher


def test_rankevent_get_valid_ranks_lower(valid_lower):
    rank_event = RankEvent(RankType.LOWER, top_rank=7)
    assert rank_event.get_valid_ranks(set(ALL_RANKS)) == valid_lower


def test_rankevent_get_valid_ranks_14(valid_14):
    rank_event = RankEvent(RankType.TOPRANK, top_rank=14)
    assert rank_event.get_valid_ranks(set(ALL_RANKS)) == valid_14


def test_rankevent_get_valid_ranks_invisible_on_14(valid_14):
    rank_event = RankEvent(RankType.TOPRANK, top_rank=14)
    valid = rank_event.get_valid_ranks(set(ALL_RANKS))
    rank_event_invisible = RankEvent(RankType.KEEPCURRENT, top_rank=SpecialRank.INVISIBLE)
    assert rank_event_invisible.get_valid_ranks(valid) == valid_14


def test_rankevent_get_valid_ranks_invisible_on_lower(valid_lower):
    rank_event = RankEvent(RankType.LOWER, top_rank=7)
    valid = rank_event.get_valid_ranks(set(ALL_RANKS))
    rank_event_invisible = RankEvent(RankType.KEEPCURRENT, top_rank=SpecialRank.INVISIBLE)
    assert rank_event_invisible.get_valid_ranks(valid) == valid_lower


def test_rankevent_get_valid_ranks_invisible_on_empty(valid_all):
    rank_event_invisible = RankEvent(RankType.KEEPCURRENT, top_rank=SpecialRank.INVISIBLE)
    assert rank_event_invisible.get_valid_ranks(valid_all) == valid_all


def test_burn_event_process(card_2h):
    play_pile = PileOfCards([card_2h])
    event = BurnEvent.YES
    event.process(play_pile)
    assert play_pile.is_empty()


def test_rankevent_process(valid_14):
    rank_event = RankEvent(RankType.TOPRANK, top_rank=14)
    input = set(ALL_RANKS)
    rank_event.process(input)
    assert input == valid_14
