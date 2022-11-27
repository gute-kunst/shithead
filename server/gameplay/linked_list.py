from copy import deepcopy
from typing import List, Optional


class Node:
    def __init__(self, data):
        self.data = data
        self.next: Optional[Node] = None
        self.previous: Optional[Node] = None

    def __repr__(self):
        return str(self.data)


class CircularDoublyLinkedList:
    def __init__(self, inputlist: List):
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

    def remove_node(self, node_data):
        """
        Doesnt remove last node"""
        if self.head is None:
            raise Exception("List is empty")
        if self.head.data == node_data:
            self.head.next.previous = self.head.previous
            self.head.previous.next = self.head.next
            self.head = self.head.next
            return
        for node in self:
            if node.data == node_data:
                node.previous.next = node.next
                node.next.previous = node.previous
                return

        raise Exception("Node with data '%s' not found" % node_data)

    def traverse_single(self, starting_point=None):
        if starting_point is None:
            starting_point = self.head
        node = starting_point
        while node is not None and (node.next != starting_point):
            yield node
            node = node.next
        yield node

    def __len__(self):
        return len([None for node in self.traverse_single()])

    def __iter__(self):  # WARNING: endless loop
        node = self.head
        while node is not None:
            yield node
            node = node.next

    def __repr__(self):
        nodes = []
        for node in self.traverse_single():
            nodes.append(str(node))
        nodes.append(str(node.next))
        return " -> ".join(nodes)

    def __getitem__(self, player_id):
        for node in self.traverse_single():
            if node.data.id == player_id:
                return node.data
