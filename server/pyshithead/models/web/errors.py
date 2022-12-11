from typing import Optional


class PyshitheadWebError(Exception):
    def __init__(self, message: str, object_id: Optional[str] = None):
        self.message = message
        self.object_id = object_id
        super().__init__(self.message)


class GameTableNotFoundError(PyshitheadWebError):
    def __init__(self, game_table_id):
        super().__init__(message="GameTableNotFound", object_id=game_table_id)
