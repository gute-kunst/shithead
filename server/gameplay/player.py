from gameplay import SetOfCards


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
