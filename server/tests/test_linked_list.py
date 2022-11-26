import pytest

from gameplay import CircularDoublyLinkedList, Player


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
    for i, node in enumerate(llist.traverse()):
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
    for i, node in enumerate(llist.traverse()):
        assert node.data == manual[del_player][i]["current"]
        assert node.next.data == manual[del_player][i]["next"]
        assert node.previous.data == manual[del_player][i]["previous"]
