import random

from pyshithead import Card, SpecialRank


class PileOfCards:
    def __init__(self, cards: list[Card] = []):
        self.cards: list[Card] = []
        for card in cards:
            self.cards.append(card)

    def shuffle(self):
        random.shuffle(self.cards)

    def take_from_top(self, nbr_of_cards=int) -> list:
        "returns card from the top ('[0]') of the tower"
        retval = self.cards[:nbr_of_cards]
        del self.cards[:nbr_of_cards]
        return retval

    def look_from_top(self, nbr_of_cards=int) -> list:
        return self.cards[:nbr_of_cards]

    def take_all(self) -> list:
        retval = self.cards[:]
        del self.cards[:]
        return retval

    def is_empty(self):
        return True if len(self.cards) == 0 else False

    def put(self, cards: set | list):
        self.cards[0:0] = cards

    def four_of_same_rank_from_top(self) -> bool:
        if len(self.cards) < 3:
            return False
        top_rank = self.cards[0].rank
        rank_counter = 1
        for card in self.cards[1:]:
            if card.rank == top_rank:
                rank_counter += 1
                if rank_counter == 4:
                    return True
                continue
            if card.rank == SpecialRank.INVISIBLE:
                continue
            elif card.rank != top_rank:
                return False
        return False

    def __len__(self):
        return len(self.cards)

    def __getitem__(self, index):
        return self.cards[index]
