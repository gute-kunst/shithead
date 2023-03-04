import asyncio
import json
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Optional

import model as m
import websockets
from PyInquirer import prompt

none_card = m.CardModel(rank=0, suit=0)  # TakePlayPile, HiddenCard


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


def prompt_and_validate_length(questions, validator: Validator):
    while True:
        selection = prompt(questions)["selection"]
        if validator.checked(len(selection)):
            return selection
        else:
            validator.error_message()


async def ainput(prompt: str = ""):
    with ThreadPoolExecutor(1, "ainput") as executor:
        return (await asyncio.get_event_loop().run_in_executor(executor, input, prompt)).rstrip()


@dataclass
class Client:
    private_info: Optional[m.PrivateInfo]
    public_info: Optional[m.PublicInfo]
    rules: Optional[m.Rules]
    players: list[int] = field(default_factory=list)
    id_: Optional[int] = None
    cards_not_chosen: bool = True

    def my_turn(self):
        return self.public_info.data.currents_turn == self.id_

    async def start_game(self):
        start_game = await ainput("start game [y/n]: ")
        if start_game == "y":
            return json.dumps({"type": "start_game"})

    def choose_cards(self):
        print("👉 SELECT PUBLIC CARDS")
        choices = [
            {"name": str(card), "value": card, "checked": False}
            for card in self.private_info.data.private_cards
        ]
        questions = [
            {
                "type": "checkbox",
                "name": "selection",
                "message": "Choose your cards",
                "choices": choices,
            }
        ]
        selection = prompt_and_validate_length(questions, ShouldBeValidator(3))
        self.cards_not_chosen = False
        return m.ChoosePublicCardsRequest(player_id=self.id_, cards=selection).json()

    def create_play_options(self):
        play_options = [
            {"name": str(card), "value": {"type": "private_cards", "card": card}}
            for card in self.private_info.data.private_cards
        ]
        if len(self.private_info.data.private_cards) == 0:
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
        card_selection = prompt_and_validate_length(questions, ShouldBeGreaterThanValidator(0))
        high_low_choice = ""
        if card_selection[0]["card"].rank == self.rules.data.high_low_rank:
            questions = [
                {
                    "type": "list",
                    "name": "high_low",
                    "choices": [
                        {"name": "Higher", "value": self.rules.data.choice.higher},
                        {"name": "Lower", "value": self.rules.data.choice.lower},
                    ],
                    "message": "Action",
                }
            ]
            high_low_choice = prompt(questions)["high_low"]
        return (card_selection, high_low_choice)

    def game_play(self):
        play_options = self.create_play_options()
        (card_selection, high_low_choice) = self.prompt_user_options(play_options)
        if card_selection[0]["type"] == "take_play_pile":
            req = m.TakePlayPileRequest(player_id=self.id_)
        elif card_selection[0]["type"] == "hidden_card":
            req = m.HiddenCardRequest(player_id=self.id_)
        else:
            req = m.PrivateCardsRequest(
                player_id=self.id_,
                cards=[x["card"] for x in card_selection],
                choice=high_low_choice,
            )
            return req.json()

    def consumer(self, message: str):
        if message is not None:
            event = json.loads(message)
            if event["type"] == "player_id":
                self.id_ = event["player_id"]
                print(f"my id : {self.id_}")
            if event["type"] == "player":
                self.players = event["data"]["players"]
                print(event["message"])
                print(f"all players : {self.players}")
            if event["type"] == "public_info":
                self.public_info = m.PublicInfo(**event)
                print("PUBLIC INFO: ", self.public_info)
            elif event["type"] == "private_info":
                self.private_info = m.PrivateInfo(**event)
                print("PRIVATE INFO: ", self.private_info)
            elif event["type"] == "rules":
                self.rules = m.Rules(**event)
                print("RULES: ", self.rules)

    async def consumer_handler(self, websocket):
        while True:
            self.consumer(await websocket.recv())

    async def producer(self):
        await asyncio.sleep(1)
        if self.public_info is None:
            return await self.start_game()
        else:
            print(self.public_info.data.game_state)
            if (
                self.public_info.data.game_state == "PLAYERS_CHOOSE_PUBLIC_CARDS"
                and self.cards_not_chosen is True
            ):
                return self.choose_cards()
            elif self.public_info.data.game_state == "DURING_GAME" and self.my_turn():
                print("DURING GAME")
                return self.game_play()

    async def producer_handler(self, websocket):
        while True:
            message = await self.producer()
            if message is not None:
                await websocket.send(message)

    async def handler(self, websocket):
        consumer_task = asyncio.create_task(self.consumer_handler(websocket))
        producer_task = asyncio.create_task(self.producer_handler(websocket))
        done, pending = await asyncio.wait(
            [consumer_task, producer_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()


async def main():
    client = Client(None, None, None)
    join_game_id = int(input("insert game id to join game: "))
    uri = f"ws://localhost:8000/game/{join_game_id}"
    async with websockets.connect(uri) as websocket:
        await client.handler(websocket)


if __name__ == "__main__":
    asyncio.run(main())
