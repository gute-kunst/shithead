import asyncio
import json
from dataclasses import dataclass, field
from typing import Optional

import model as m
import websockets
from rich.columns import Columns
from rich.markdown import Markdown
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Header, Input, Static, TextLog


@dataclass
class Client:
    private_info: Optional[m.PrivateInfo]
    public_info: Optional[m.PublicInfo]
    rules: Optional[m.Rules]
    players: list[int] = field(default_factory=list)
    id_: int = -1
    cards_not_chosen: bool = True

    # def game_play(self):
    #     play_options = self.create_play_options()
    #     (card_selection, high_low_choice) = self.prompt_user_options(play_options)
    #     if card_selection[0]["type"] == "take_play_pile":
    #         req = m.TakePlayPileRequest(player_id=self.id_)
    #     elif card_selection[0]["type"] == "hidden_card":
    #         req = m.HiddenCardRequest(player_id=self.id_)
    #     else:
    #         req = m.PrivateCardsRequest(
    #             player_id=self.id_,
    #             cards=[x["card"] for x in card_selection],
    #             choice=high_low_choice,
    #         )
    #         return req.json()

    def consumer(self, message: str):
        if message is not None:
            event = json.loads(message)
            if event["type"] == "client_id":
                self.id_ = event["client_id"]
            if event["type"] == "player":
                self.players = event["data"]["clients"]
            if event["type"] == "public_info":
                self.public_info = m.PublicInfo(**event)
            elif event["type"] == "private_info":
                self.private_info = m.PrivateInfo(**event)
            elif event["type"] == "rules":
                self.rules = m.Rules(**event)

    async def consumer_handler(self, websocket):
        while True:
            self.consumer(await websocket.recv())

    async def producer(self):
        await asyncio.sleep(1)
        # if self.public_info is None:
        #     return await self.start_game()
        # else:
        #     print(self.public_info.data.game_state)
        #     if (
        #         self.public_info.data.game_state == "PLAYERS_CHOOSE_PUBLIC_CARDS"
        #         and self.cards_not_chosen is True
        #     ):
        #         return self.choose_cards()
        #     elif self.public_info.data.game_state == "DURING_GAME" and self.my_turn():
        #         print("DURING GAME")
        # return self.game_play()

    async def producer_handler(self, websocket):
        while True:
            app.write_log("ping from producer")
            await asyncio.sleep(1)

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


class Card(Static):
    def __init__(self, suit: str = "♥", rank: str = "3") -> None:
        super().__init__("")
        self.suit = suit
        self.rank = rank

    def compose(self) -> ComposeResult:
        app.write_log(f"{self.suit} {self.rank}")
        yield Static(f"{self.suit} {self.rank}")


class Player(Static):
    private = 5
    public = 3
    hidden = 3
    player_id = 1
    player_name = "Blue-Ocean"

    def compose(self) -> ComposeResult:
        app.write_log("creating player")
        with Vertical(id="player"):
            yield Static(Markdown(f"### {self.player_name} ({self.player_id})"))
            yield Static(Columns([f"👋 {self.private}", f"🙈 {self.hidden}"]))
            with Horizontal(classes="private-cards-container"):
                yield Card("♣", "5")
                yield Card("♥", "10")
                yield Card("♦", "Q")

    def on_click(self):
        self.private = 10
        self.update()


class Game(Static):
    def compose(self) -> ComposeResult:
        with Container(id="sidebar"):
            # yield Static("Players", id="player-heading")
            yield Player()

        with Horizontal():
            yield Input(placeholder="Enter a Game ID", id="game-id", classes="column")
            yield Button("JOIN GAME(not working)", id="join-game")
        yield Button("2")
        yield Button("3")

    async def on_input_submitted(self, event: Input.Submitted):
        try:
            game_id: int = int(event.value)
        except:
            raise ValueError("game id not int parsable")

        app.log(f"joining game: {game_id}")
        await app.connect_to_game(game_id)


class ShitheadApp(App):
    CSS_PATH = "shithead.css"
    client: Client = Client(None, None, None)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Container(id="panel", classes="column"):
                yield Game(id="welcome")
            with Container(id="log", classes="column"):
                yield Static(Markdown("## Log"))
                yield TextLog(
                    highlight=True,
                    markup=True,
                )

    def on_mount(self):
        self.write_log("init ...")

    def on_key(self, key) -> None:
        self.write_log(f"log message ... {key}")

    def write_log(self, message):
        text_log = self.query_one(TextLog)
        text_log.write(message)

    async def connect_to_game(self, game_id: int):
        uri = f"ws://localhost:8000/game/{game_id}"
        async with websockets.connect(uri) as websocket:
            await self.client.handler(websocket)


if __name__ == "__main__":
    app = ShitheadApp()
    app.run()
