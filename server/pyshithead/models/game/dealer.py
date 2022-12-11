from pyshithead.models.game import (
    ALL_RANKS,
    NBR_HIDDEN_CARDS,
    Card,
    CircularDoublyLinkedList,
    PileOfCards,
    Player,
    SetOfCards,
    Suit,
)


class Dealer:
    def __init__(self) -> None:
        pass

    @classmethod
    def deal_cards_to_players(
        cls,
        deck: PileOfCards,
        active_players: CircularDoublyLinkedList | list[Player],
        put_public_to_private=True,
    ):
        for player in active_players:
            player.hidden_cards = SetOfCards(deck.take_from_top(NBR_HIDDEN_CARDS))
            if put_public_to_private:
                player.private_cards = SetOfCards(deck.take_from_top(NBR_HIDDEN_CARDS * 2))
            else:
                player.private_cards = SetOfCards(deck.take_from_top(NBR_HIDDEN_CARDS))
                player.public_cards = SetOfCards(deck.take_from_top(NBR_HIDDEN_CARDS))

    @classmethod
    def provide_shuffled_deck(cls, ranks=ALL_RANKS, suits=Suit) -> PileOfCards:
        deck = cls.provide_deck(ranks, suits)
        deck.shuffle()
        return deck

    @classmethod
    def provide_deck(cls, ranks=ALL_RANKS, suits=Suit) -> PileOfCards:
        return PileOfCards([Card(i, suit) for suit in suits for i in ranks])

    @classmethod
    def fillup_cards(cls, deck: PileOfCards, player: Player):
        while len(player.private_cards) < NBR_HIDDEN_CARDS:
            if len(deck) > 0:
                player.private_cards.put(deck.take_from_top(1))
            elif len(deck) == 0:
                if not player.private_cards.is_empty():
                    return
                else:  ## CHECK PUBLIC CARDS
                    if not player.public_cards.is_empty():
                        player.private_cards.put(player.public_cards.take_all())
                        print("👍 Took public cards")
                    return
