from __future__ import print_function, unicode_literals

from typing import Optional

from prompt_toolkit.validation import ValidationError, Validator
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
    def __init__(self, nbr_of_players):
        players = [Player(id) for id in range(0, nbr_of_players)]
        self.game = Game.initialize(players, ranks=list(range(2, 8)))
        # self.game = Game.initialize(players))
        print("game initialized")
        print(self.game)

    def get_private_infos(self, player_id: Optional[int] = None):
        return self.game.get_player(player_id).get_private_info()

    def get_public_infos(self):
        return dict(
            {
                "game_id": self.game.game_id,
                "playpile": self.game.play_pile,
                "nbr_of_cards_in_deck": len(self.game.deck),
                "currents_turn": self.game.get_player().id_,
                "player_public_info": [
                    player.get_public_info() for player in self.game.active_players
                ],
            }
        )

    def process_request(self, req: dict):
        player = self.game.get_player(req["player_id"])
        print(player)
        if req["type"] == "choose_public_cards":
            self.game.process_playrequest(ChoosePublicCardsRequest.from_dict(player, req))
        if req["type"] == "private_cards":
            self.game.process_playrequest(PrivateCardsRequest.from_dict(player, req))
        if req["type"] == "take_play_pile":
            self.game.process_playrequest(TakePlayPileRequest(player))
        if req["type"] == "hidden_card":
            self.game.process_playrequest(HiddenCardRequest(player))

    def start(self):
        for player in self.game.active_players:
            print(f"Select public cards for player {player.id_} ... ")
            private_cards = self.get_private_infos(player.id_)["private_cards"]
            choices = [
                {"name": str(card), "value": card, "checked": False} for card in private_cards
            ]
            questions = [
                {
                    "type": "checkbox",
                    "name": "choose_public",
                    "message": "Choose your cards",
                    "choices": choices,
                }
            ]
            repeat_input = True
            while repeat_input:
                chosen_cards = prompt(questions)["choose_public"]
                if len(chosen_cards) != 3:
                    repeat_input = True
                    print("👉 Select 3 cards")
                else:
                    repeat_input = False
            print(chosen_cards)
            req = dict(
                {
                    "type": "choose_public_cards",
                    "player_id": player.id_,
                    "cards": chosen_cards,
                }
            )
            self.process_request(req)
        View.show_game(self.game)
        while -1:
            broadcast_msg = self.get_public_infos()
            private_msg = self.get_private_infos(broadcast_msg["currents_turn"])

            # player = self.game.get_player()
            print(f"Turn Player: {broadcast_msg['currents_turn']}")
            move_options = [
                {"name": str(card), "value": card} for card in private_msg["private_cards"]
            ]
            special_take_tower_card = vars(Card(0, Suit.HEART))
            play_hidden_card = vars(Card(1, Suit.HEART))
            if len(private_msg["private_cards"]) == 0:
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
            repeat_input = True
            while repeat_input:
                chosen_cards = prompt(questions)["play_card"]
                if len(chosen_cards) == 0:
                    repeat_input = True
                    print("👉 Select at least 1 option")
                else:
                    repeat_input = False
            high_low_choice = None
            if chosen_cards[0]["rank"] == SpecialRank.HIGHLOW:
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
                if chosen_cards[0]["rank"] == 0:
                    req = dict({"type": "take_play_pile", "player_id": private_msg["id"]})
                elif chosen_cards[0]["rank"] == 1:
                    req = dict({"type": "hidden_card", "player_id": private_msg["id"]})
                else:
                    req = dict(
                        {
                            "type": "private_cards",
                            "player_id": private_msg["id"],
                            "cards": chosen_cards,
                            "choice": high_low_choice,
                        }
                    )
                self.process_request(req)
            except PyshitheadError as err:
                print(f"🔥 Error: {err.message} 👉 Try Again")
            View.show_game(self.game)

        print("done")


if __name__ == "__main__":
    print("⭐⭐ Shithead Game ⭐⭐")
    nbr_of_players = int(input("Nbr of players: "))
    controller = Controller(nbr_of_players)
    controller.start()
