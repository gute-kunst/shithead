import random
from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set, Union

NBR_HIDDEN_CARDS = 3
TOTAL_NBR_OF_CARDS = 52


class Suit(Enum):
    TILES = 1
    HEART = 2
    CLOVERS = 3
    PIKES = 4


class RequestPileSpecialty(Enum):
    HIGHER = 1
    LOWER = 2


@dataclass(frozen=True)
class Card:
    rank: int
    suit: Suit

    def __hash__(self):
        return hash(str(self.rank) + str(self.suit))

    def __eq__(self, other):
        return self.rank == other.rank and self.suit == other.suit


class SetOfCards:
    def __init__(self, cards: Union[Set, List] = set()):
        self.cards: Set[Card] = set(cards)

    # specialty: RequestPileSpecialty = RequestPileSpecialty()

    def rank_is_equal(self):
        return all(card.rank == list(self.cards)[0].rank for card in self.cards)

    def __contains__(self, other):
        return other.cards.issubset(self.cards)

    def __len__(self):
        return len(self.cards)

    def is_empty(self):
        return True if len(self.cards) == 0 else False

    def add(self, cards: Union[Set, List]):
        self.cards.update(cards)


class PileOfCards:
    def __init__(self, cards: list[Card] = []):
        self.cards = cards

    def shuffle(self):
        random.shuffle(self.cards)

    def take(self, nbr_of_cards=int) -> list:
        retval = self.cards[:nbr_of_cards]
        del self.cards[:nbr_of_cards]
        return retval

    def take_all(self) -> list:
        retval = self.cards[:]
        del self.cards[:]
        return retval

    def is_empty(self):
        return True if len(self.cards) == 0 else False

    def __len__(self):
        return len(self.cards)

    @classmethod
    def generate_deck(cls):
        deck = PileOfCards([Card(i, suit) for suit in Suit for i in range(2, 15)])
        # deck = PileOfCards([Card(i, suit) for suit in Suit for i in range(1, 3)])

        deck.shuffle()
        return deck


class Player:
    def __init__(self, id: int):
        self.id: int = id
        self.public_cards = SetOfCards()
        self.hidden_cards = SetOfCards()
        self.private_cards = SetOfCards()

    def __repr__(self):
        return str(self.id)

    def __eq__(self, other):
        return self.id == other.id


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


class Game:
    def __init__(self, players: list[Player]):
        if len(players) > 5:
            raise ValueError("too many players")
        self.players = players
        self.deck = PileOfCards.generate_deck()
        self.play_pile = PileOfCards()

    def deal_cards(self):
        for player in self.players:
            player.hidden_cards.add(self.deck.take(NBR_HIDDEN_CARDS))
            player.private_cards.add(self.deck.take(NBR_HIDDEN_CARDS * 2))


# players = [Player(1), Player(2), Player(3)]
# game = Game(players)
# print(game.players)

# game.deal_cards()


# pile1 = SetOfCards()

# # pile1 = SetOfCards({Card(3, Suit.TILES), Card(4, Suit.TILES)})

# pile2 = SetOfCards([Card(3, Suit.TILES), Card(3, Suit.TILES)])
# pile1.cards.update(pile2.cards)
# print(pile2 in pile1)

# # print(set1.issubset(set2))
# # print(hash(Card(3, Suit.TILES)))

# print(pile1.rank_is_equal())


# def _card_2t():
#     return Card(2, Suit.TILES)


# card1 = _card_2t()

# # print(pile2 in pile1)
# print("finished")
