from pyshithead import GAME_ID

from .game_table import GameTable


class GameTablesManager:
    def __init__(self):
        self.game_tables: list[GameTable] = [GameTable(game_id=GAME_ID)]

    async def get_game_table_by_id(self, game_id: int) -> GameTable:
        print("only 1 game supported for now")
        return self.game_tables[0]
        # raise GameTableNotFoundError(game_id)

    def add_game_table(self):
        raise NotImplementedError
