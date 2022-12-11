from __future__ import print_function, unicode_literals

from PyInquirer import prompt

from pyshithead.models.game import (
    Card,
    Choice,
    ChoosePublicCardsRequest,
    Game,
    HiddenCardRequest,
    Player,
    PrivateCardsRequest,
    PyshitheadError,
    SpecialRank,
    Suit,
    TakePlayPileRequest,
    View,
)


class Controller:
    def __init__(self, view=None):
        self.view = view
        self.game_model: Game = None

    def start(self):
        nbr_of_players = int(input("Nbr of players: "))
        players = [Player(id) for id in range(0, nbr_of_players)]
        self.game = Game.initialize(players, ranks=list(range(2, 7)))
        print("game initialized")
        print(self.game)
        for player in self.game.active_players:
            print(f"Select public cards for player {player.id_} ... ")
            choices = [
                {"name": str(card), "value": card, "checked": False}
                for card in list(player.private_cards)
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
            req = ChoosePublicCardsRequest(player, chosen_cards)
            self.game.process_playrequest(req)
        View.show_game(self.game)
        while -1:
            player = self.game.get_player()
            print(f"Turn Player: {player.id_}")
            move_options = [
                {"name": str(card), "value": card} for card in list(player.private_cards)
            ]
            special_take_tower_card = Card(0, Suit.HEART)
            play_hidden_card = Card(1, Suit.HEART)
            if len(player.private_cards) == 0:
                move_options.insert(0, {"name": "Play Hidden Card", "value": play_hidden_card})
            else:
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
            try:
                if chosen_cards[0].rank == 0:
                    req = TakePlayPileRequest(player)
                elif chosen_cards[0].rank == 1:
                    req = HiddenCardRequest(player)
                else:
                    req = PrivateCardsRequest(player, chosen_cards, high_low_choice)
                self.game.process_playrequest(req)
            except PyshitheadError as err:
                print(f"🔥 Error: {err.message} 👉 Try Again")
            View.show_game(self.game)

        print("done")


if __name__ == "__main__":
    print("Shithead Game")
    controller = Controller()
    controller.start()
