from copy import deepcopy
from typing import Optional

from pyshithead.models.game.errors import LinkedListEmptyError, LinkedListNodeNotFoundError


class Node:
    def __init__(self, data):
        self.data = data
        self.next: Optional[Node] = None
        self.previous: Optional[Node] = None

    def __repr__(self):
        return str(self.data)


class CircularDoublyLinkedList:
    def __init__(self, input_list: list):
        tmp_input = deepcopy(input_list)
        self.head = None
        if tmp_input is not None:
            node = Node(data=tmp_input.pop(0))
            self.head = node
            for elem in tmp_input:
                node.next = Node(data=elem)
                node.next.previous = node
                node = node.next
            node.next = self.head
            self.head.previous = node

    def remove_node(self, node_data):
        """
        Doesn't remove last node"""
        if self.head is None:
            raise LinkedListEmptyError
        if self.head.data == node_data:
            self.head.next.previous = self.head.previous
            self.head.previous.next = self.head.next
            self.head = self.head.next
            return
        for node in self.traverse_endless():
            if node.data == node_data:
                node.previous.next = node.next
                node.next.previous = node.previous
                return
        raise LinkedListNodeNotFoundError

    def get_ordered_list(self) -> list:
        return [node for node in self]

    def traverse_single(self, starting_point=None):
        """
        traverse linked list with yielding the node (not node.data)
        """
        if starting_point is None:
            starting_point = self.head
        node = starting_point
        while node is not None and (node.next != starting_point):
            yield node
            node = node.next
        yield node

    def traverse_endless(self):
        """
        endless loop
        """
        node = self.head
        while node is not None:
            yield node
            node = node.next

    def next(self, times: int = 1):
        for x in range(times):
            self.head = self.head.next

    def __len__(self):
        return len([None for node in self])

    def __iter__(self):
        """
        traverse linked list once (no endless loop) with yielding node.data.
        """
        starting_point = self.head
        node = starting_point
        while node is not None and (node.next != starting_point):
            yield node.data
            node = node.next
        yield node.data

    def __repr__(self):
        nodes = []
        for node in self.traverse_single():
            nodes.append(str(node))
        nodes.append(str(node.next))
        return " -> ".join(nodes) + " ..."

    def __getitem__(self, player_id):
        for node in self:
            if node.id_ == player_id:
                return node
