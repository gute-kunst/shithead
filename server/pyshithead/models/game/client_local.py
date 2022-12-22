import time
from typing import Optional

from PyInquirer import prompt
from pyshithead.models.game import GameManager, View
from pyshithead.models.game.errors import PyshitheadError

none_card: dict = dict({"rank": None, "suit": None})


class ClientLocal:
    """
    Mimics a client. This class should have no dependency other than the controller.
    """

    def __init__(self):
        self.manager: Optional[GameManager] = None
        self.rules: dict

    def start(self):
        print("⭐⭐ Shithead Game ⭐⭐")
        nbr_of_players = int(input("Nbr of players: "))
        self.manager = GameManager(nbr_of_players)
        self.rules = self.manager.get_rules()
        for player in self.manager.game.active_players:
            print(f"Select public cards for player {player.id_} ... ")
            private_cards = self.manager.get_private_infos(player.id_)["private_cards"]
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
                selection = prompt(questions)["choose_public"]
                if len(selection) != 3:
                    repeat_input = True
                    print("👉 Select 3 cards")
                else:
                    repeat_input = False
            print(selection)
            req = dict(
                {
                    "type": "choose_public_cards",
                    "player_id": player.id_,
                    "cards": selection,
                }
            )
            self.manager.process_request(req)
        View.show_game(self.manager.game)
        while -1:
            broadcast_msg = self.manager.get_public_infos()
            private_msg = self.manager.get_private_infos(broadcast_msg["currents_turn"])
            if broadcast_msg["state"] == "GAME_OVER":
                exit()
            # player = self.ctrl.game.get_player()
            print(f"Turn Player: {broadcast_msg['currents_turn']}")
            move_options = [
                {"name": str(card), "value": {"type": "private_cards", "card": card}}
                for card in private_msg["private_cards"]
            ]
            if len(private_msg["private_cards"]) == 0:
                move_options.insert(
                    0,
                    {
                        "name": "Play Hidden Card",
                        "value": {"type": "hidden_card", "card": none_card},
                    },
                )
            else:
                move_options.insert(
                    0, {"name": "Take Pile", "value": {"type": "take_play_pile", "card": none_card}}
                )

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
                selection = prompt(questions)["play_card"]
                if len(selection) == 0:
                    repeat_input = True
                    print("👉 Select at least 1 option")
                else:
                    repeat_input = False
            high_low_choice = None
            if selection[0]["card"]["rank"] == self.rules["special_rank"]["high_low"]:
                questions = [
                    {
                        "type": "list",
                        "name": "high_low",
                        "choices": [
                            {"name": "Higher", "value": self.rules["choice"]["higher"]},
                            {"name": "Lower", "value": self.rules["choice"]["lower"]},
                        ],
                        "message": "Action",
                    }
                ]
                high_low_choice = prompt(questions)["high_low"]
            try:
                if selection[0]["type"] == "take_play_pile":
                    req = dict({"type": "take_play_pile", "player_id": private_msg["id"]})
                elif selection[0]["type"] == "hidden_card":
                    req = dict({"type": "hidden_card", "player_id": private_msg["id"]})
                else:
                    req = dict(
                        {
                            "type": "private_cards",
                            "player_id": private_msg["id"],
                            "cards": [x["card"] for x in selection],
                            "choice": high_low_choice,
                        }
                    )
                self.manager.process_request(req)
            except PyshitheadError as err:
                print(f"🔥 Error: {err.message} 👉 Try Again")
            print("pass local client to next player ...")
            time.sleep(1)
            View.show_game(self.manager.game)


if __name__ == "__main__":
    client = ClientLocal()
    client.start()
