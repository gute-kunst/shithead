import asyncio
import json
from dataclasses import dataclass, field
from typing import Optional

import model as m
import websockets
from rich.columns import Columns
from rich.markdown import Markdown
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Button, Header, Input, Static, TextLog


@dataclass
class Client:
    private_info: Optional[m.PrivateInfo]
    public_info: Optional[m.PublicInfo]
    rules: Optional[m.Rules]
    players: list[int] = field(default_factory=list)
    id_: int = -1
    cards_not_chosen: bool = True

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
            if event["type"] == "client_id":
                self.id_ = event["client_id"]
                print(f"my id : {self.id_}")
            if event["type"] == "player":
                self.players = event["data"]["clients"]
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
            app.update_log("pong from consumer")
            await asyncio.sleep(0.3)

        # while True:
        #     self.consumer(await websocket.recv())

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
            app.update_log("ping from producer")
            await asyncio.sleep(0.3)

            # message = await self.producer()
            # if message is not None:
            #     await websocket.send(message)

    async def handler(self, websocket):
        consumer_task = asyncio.create_task(self.consumer_handler(websocket))
        producer_task = asyncio.create_task(self.producer_handler(websocket))
        done, pending = await asyncio.wait(
            [consumer_task, producer_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()


# class Player(Static):
#     private = 5
#     public = 3
#     hidden = 3
#     player_id = 1
#     player_name = "Blue-Ocean"

#     def on_mount(self) -> ComposeResult:

#         yield Static(Markdown(f"# {self.player_name}"))
#         yield Static(f"id: {self.player_id}")
#         yield Static(Columns([f"👋 {self.private}", f"👀 {self.public}", f"🙈 {self.hidden}"]))

#     def on_click(self):
#         self.private = 10
#         self.update()


class Welcome(Static):
    def compose(self) -> ComposeResult:
        yield Static(Markdown(f"# Shithead"))
        with Horizontal():
            yield Input(placeholder="Enter a Game ID", id="game-id", classes="column")
            yield Button("JOIN GAME(not working)", id="join-game")

    async def on_input_submitted(self, event: Input.Submitted):
        try:
            game_id: int = int(event.value)
        except:
            raise ValueError("game id not int parsable")

        app.update_log(f"joining game: {game_id}")
        await app.connect_to_game(game_id)


class ShitheadApp(App):
    CSS_PATH = "shithead.css"
    client: Client = Client(None, None, None)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Container(id="panel", classes="column"):
                yield Welcome(id="welcome")
            with Container(id="log", classes="column"):
                yield Static(Markdown("## Log"))
                yield TextLog(
                    highlight=True,
                    markup=True,
                )

    def on_mount(self):
        self.update_log("init ...")

    def on_key(self, key) -> None:
        self.update_log(f"log message ... {key}")

    def update_log(self, message):
        text_log = self.query_one(TextLog)
        text_log.write(message)

    async def connect_to_game(self, game_id: int):
        uri = f"ws://localhost:8000/game/{game_id}"
        async with websockets.connect(uri) as websocket:
            await self.client.handler(websocket)


if __name__ == "__main__":
    app = ShitheadApp()
    app.run()
