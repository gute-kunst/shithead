from copy import deepcopy
from typing import List, Optional

from gameplay import Player


class Node:
    def __init__(self, data: Player):
        self.data: Player = data
        self.next: Optional[Node] = None
        self.previous: Optional[Node] = None

    def __repr__(self):
        return str(self.data)


class CircularDoublyLinkedList:
    def __init__(self, inputlist: List[Player]):
        tmp_input = deepcopy(inputlist)
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

    def remove_player(self, player):
        if self.head is None:
            raise Exception("List is empty")

        if self.head.data == player:
            self.head.next.previous = self.head.previous
            self.head.previous.next = self.head.next
            self.head = self.head.next
            return
        for node in self:
            if node.data == player:
                node.previous.next = node.next
                node.next.previous = node.previous
                return

        raise Exception("Node with data '%s' not found" % player)

    def traverse(self, starting_point=None):
        if starting_point is None:
            starting_point = self.head
        node = starting_point
        while node is not None and (node.next != starting_point):
            yield node
            node = node.next
        yield node

    def __len__(self):
        return len([None for node in self.traverse()])

    def __iter__(self):  # endless loop
        node = self.head
        while node is not None:
            yield node
            node = node.next

    def __repr__(self):
        nodes = []
        for node in self.traverse():
            nodes.append(str(node))
        nodes.append(str(node.next))
        return " -> ".join(nodes)
