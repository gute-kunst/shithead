import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from PyInquirer import prompt

from pyshithead.models.game import GameManager, View
from pyshithead.models.game.errors import PyshitheadError

none_card: dict = dict({"rank": None, "suit": None})


@dataclass
class Validator(ABC):
    rhs: int

    @abstractmethod
    def checked(self, value: int):
        pass

    @abstractmethod
    def error_message(self):
        pass


class ShouldBeValidator(Validator):
    def checked(self, value: int):
        return value == self.rhs

    def error_message(self):
        print(f"👉 Select exactly {self.rhs} options")


class ShouldBeGreaterThanValidator(Validator):
    def checked(self, value: int):
        return value != self.rhs

    def error_message(self):
        print(f"👉 Select {self.rhs+1} or more options")


class ClientLocal:
    """
    Mimics a client. This class should have no dependency other than the GameManager.
    """

    def __init__(self):
        self.manager: Optional[GameManager] = None
        self.rules: dict
        self.public_info: dict
        self.private_info: dict

    def send_and_update(self, req):
        try:
            self.manager.process_request(req)
        except PyshitheadError as err:
            print(f"🔥 Error: {err.message} 👉 Try Again")
        print("pass local client to next player ...")
        time.sleep(1)
        self.public_info = self.manager.get_public_infos()["data"]
        self.private_info = self.manager.get_private_infos(self.public_info["currents_turn"])[
            "data"
        ]
        self.check_game_over()
        View.show_public_info(self.manager.get_public_infos()["data"])

    def check_game_over(self):
        if self.public_info["game_state"] == "GAME_OVER":
            exit()

    def initialize(self):
        print("⭐⭐ Shithead Game ⭐⭐")
        nbr_of_players = int(input("Nbr of players: "))
        self.manager = GameManager(list(range(nbr_of_players)))
        self.rules = self.manager.get_rules()["data"]
        self.public_info = self.manager.get_public_infos()["data"]

    def prompt_and_validate_length(self, questions, validator: Validator):
        while True:
            selection = prompt(questions)["selection"]
            if validator.checked(len(selection)):
                return selection
            else:
                validator.error_message()

    def players_choose_cards(self):
        for player in self.public_info["player_public_info"]:
            print(f"Select public cards for player {player['id']} ... ")
            private_cards = self.manager.get_private_infos(player["id"])["data"]["private_cards"]
            choices = [
                {"name": str(card), "value": card, "checked": False} for card in private_cards
            ]
            questions = [
                {
                    "type": "checkbox",
                    "name": "selection",
                    "message": "Choose your cards",
                    "choices": choices,
                }
            ]
            selection = self.prompt_and_validate_length(questions, ShouldBeValidator(3))
            print(selection)
            self.send_and_update(
                {
                    "type": "choose_public_cards",
                    "player_id": player["id"],
                    "cards": selection,
                }
            )

    def create_play_options(self):
        play_options = [
            {"name": str(card), "value": {"type": "private_cards", "card": card}}
            for card in self.private_info["private_cards"]
        ]
        if len(self.private_info["private_cards"]) == 0:
            play_options.insert(
                0,
                {
                    "name": "Play Hidden Card",
                    "value": {"type": "hidden_card", "card": none_card},
                },
            )
        else:
            play_options.insert(
                0, {"name": "Take Pile", "value": {"type": "take_play_pile", "card": none_card}}
            )
        return play_options

    def prompt_user_options(self, play_options):
        questions = [
            {
                "type": "checkbox",
                "name": "selection",
                "choices": play_options,
                "message": "Choose your cards",
            }
        ]
        card_selection = self.prompt_and_validate_length(questions, ShouldBeGreaterThanValidator(0))
        high_low_choice = None
        if card_selection[0]["card"]["rank"] == self.rules["special_rank"]["high_low"]:
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
        return (card_selection, high_low_choice)

    def game_play(self):
        while -1:
            play_options = self.create_play_options()
            (card_selection, high_low_choice) = self.prompt_user_options(play_options)
            if card_selection[0]["type"] == "take_play_pile":
                req = dict({"type": "take_play_pile", "player_id": self.private_info["id"]})
            elif card_selection[0]["type"] == "hidden_card":
                req = dict({"type": "hidden_card", "player_id": self.private_info["id"]})
            else:
                req = dict(
                    {
                        "type": "private_cards",
                        "player_id": self.private_info["id"],
                        "cards": [x["card"] for x in card_selection],
                        "choice": high_low_choice,
                    }
                )
            self.send_and_update(req)

    def run(self):
        self.initialize()
        self.players_choose_cards()
        self.game_play()


if __name__ == "__main__":
    client = ClientLocal()
    client.run()
