from __future__ import print_function, unicode_literals

from PyInquirer import prompt

from pyshithead import (
    Card,
    Choice,
    ChoosePublicCardsRequest,
    Game,
    Player,
    PrivateCardsRequest,
    SpecialRank,
    Suit,
    TakePlayPileRequest,
    View,
)


class Controller:
    def __init__(self, view=None):
        self.view = view
        self.gamemodel: Game = None

    def start(self):
        nbr_of_players = int(input("Nbr of players: "))
        players = [Player(id) for id in range(0, nbr_of_players)]
        self.game = Game(players)
        print("game initialized")
        print(self.game)
        for player in self.game.active_players.traverse_single():
            print(f"Select public cards for player {player.data.id_} ... ")
            choices = [
                {"name": str(card), "value": card, "checked": False}
                for card in list(player.data.private_cards)
            ]
            questions = [
                {
                    "type": "checkbox",
                    "name": "choose_public",
                    "choices": choices,
                    "message": "Choose your cards",
                }
            ]
            chosen_cards = prompt(questions)["choose_public"]
            print(chosen_cards)
            req = ChoosePublicCardsRequest(player.data, chosen_cards)
            self.game.process_playrequest(req)
        View.show_game(self.game)
        while -1:
            player = self.game.get_player()
            print(f"Turn Player: {player.id_}")
            move_options = [
                {"name": str(card), "value": card} for card in list(player.private_cards)
            ]
            special_take_tower_card = Card(0, Suit.HEART)
            move_options.insert(0, {"name": "Take Pile", "value": special_take_tower_card})
            questions = [
                {
                    "type": "checkbox",
                    "name": "play_card",
                    "choices": move_options,
                    "message": "Choose your cards",
                }
            ]
            chosen_cards = prompt(questions)["play_card"]
            high_low_choice = None
            if chosen_cards[0].rank == SpecialRank.HIGHLOW:
                questions = [
                    {
                        "type": "list",
                        "name": "high_low",
                        "choices": [
                            {"name": "Higher", "value": Choice.HIGHER},
                            {"name": "Lower", "value": Choice.LOWER},
                        ],
                        "message": "Action",
                    }
                ]
                high_low_choice = prompt(questions)["high_low"]
            if chosen_cards[0].rank == 0:
                req = TakePlayPileRequest(player)
            else:
                req = PrivateCardsRequest(player, chosen_cards, high_low_choice)
            self.game.process_playrequest(req)
            View.show_game(self.game)

        print("done")


if __name__ == "__main__":
    print("Shithead Game")
    controller = Controller()
    controller.start()
