import pytest

from pyshithead.models.game import CircularDoublyLinkedList, NextPlayerEvent, Player


def manual_llist_3(tp: list[Player]):
    return [
        {"previous": tp[2], "current": tp[0], "next": tp[1]},
        {"previous": tp[0], "current": tp[1], "next": tp[2]},
        {"previous": tp[1], "current": tp[2], "next": tp[0]},
    ]


def manual_llist_3_removed_0(tp: list[Player]):
    return [
        {"previous": tp[2], "current": tp[1], "next": tp[2]},
        {"previous": tp[1], "current": tp[2], "next": tp[1]},
    ]


def test_linked_list_init_length(two_players):
    llist = CircularDoublyLinkedList(two_players)
    assert len(llist) == 2


def test_linked_list_initialization(three_players):
    manual = manual_llist_3(three_players)
    llist = CircularDoublyLinkedList(three_players)
    for i, node in enumerate(llist.traverse_single()):
        assert node.data == manual[i]["current"]
        assert node.next.data == manual[i]["next"]
        assert node.previous.data == manual[i]["previous"]


@pytest.mark.parametrize("del_player", (0, 1, 2))
def test_linked_list_remove(del_player, three_players):
    tp = three_players
    llist = CircularDoublyLinkedList(tp)
    assert len(llist) == 3
    llist.remove_node(tp[del_player])
    assert len(llist) == 2
    manual = [
        [
            {"previous": tp[2], "current": tp[1], "next": tp[2]},
            {"previous": tp[1], "current": tp[2], "next": tp[1]},
        ],
        [
            {"previous": tp[2], "current": tp[0], "next": tp[2]},
            {"previous": tp[0], "current": tp[2], "next": tp[0]},
        ],
        [
            {"previous": tp[1], "current": tp[0], "next": tp[1]},
            {"previous": tp[0], "current": tp[1], "next": tp[0]},
        ],
    ]
    for i, node in enumerate(llist.traverse_single()):
        assert node.data == manual[del_player][i]["current"]
        assert node.next.data == manual[del_player][i]["next"]
        assert node.previous.data == manual[del_player][i]["previous"]


def test_linked_list_remove_all(three_players):
    llist = CircularDoublyLinkedList(three_players)
    llist.remove_node(three_players[0])
    llist.remove_node(three_players[1])
    assert len(llist) == 1
    llist.head.data == three_players[2]


def test_linked_list_next(three_players):
    llist = CircularDoublyLinkedList(three_players)

    next = llist.head.next
    llist.next(NextPlayerEvent.NEXT)
    assert next == llist.head

    same = llist.head
    llist.next(NextPlayerEvent.SAME)
    assert same == llist.head

    next2 = llist.head.next.next
    llist.next(NextPlayerEvent.NEXT_2)
    assert next2 == llist.head

    next3 = llist.head.next.next.next
    llist.next(NextPlayerEvent.NEXT_3)
    assert next3 == llist.head

    next4 = llist.head.next.next.next.next
    llist.next(NextPlayerEvent.NEXT_4)
    assert next4 == llist.head


def test_linked_list_get_item(three_players: list[Player]):
    llist = CircularDoublyLinkedList(three_players)
    player = llist[three_players[0].id_]
    assert player == three_players[0]
