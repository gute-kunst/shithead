from __future__ import print_function, unicode_literals

from typing import Optional

from PyInquirer import prompt

from pyshithead.models.game import (
    Choice,
    ChoosePublicCardsRequest,
    Game,
    HiddenCardRequest,
    Player,
    PrivateCardsRequest,
    SpecialRank,
    TakePlayPileRequest,
)


class Controller:
    """dictionary based interface to Game. Manages a Game"""

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
                "state": self.game.state,
                "nbr_of_cards_in_deck": len(self.game.deck),
                "currents_turn": self.game.get_player().id_,
                "player_public_info": [
                    player.get_public_info() for player in self.game.active_players
                ],
            }
        )

    def get_rules(self):
        return dict(
            {
                "special_rank": {"high_low": SpecialRank.HIGHLOW},
                "choice": {"higher": Choice.HIGHER, "lower": Choice.LOWER},
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
