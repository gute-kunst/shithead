import asyncio

import client
from rich.markdown import Markdown
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Button, Header, Input, Static, TextLog


class Welcome(Static):
    def compose(self) -> ComposeResult:
        yield Static(Markdown(f"# Shithead"))


class Shithead(App):
    CSS_PATH = "shithead.css"

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

    async def infinite_task(self):
        while True:
            await asyncio.sleep(1)
            self.update_log("ping")

    def on_mount(self):
        self.update_log("init ...")
        asyncio.create_task(self.infinite_task())

    def on_key(self, key) -> None:
        self.update_log(f"log message ... {key}")

    def update_log(self, message):
        text_log = self.query_one(TextLog)
        text_log.write(message)


if __name__ == "__main__":
    app = Shithead()
    app.run()
