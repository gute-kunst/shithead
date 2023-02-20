# from __future__ import print_function, unicode_literals

from typing import Optional

from pyshithead.models.common import request_models
from pyshithead.models.game import (
    ChoosePublicCardsRequest,
    Game,
    HiddenCardRequest,
    Player,
    PrivateCardsRequest,
    TakePlayPileRequest,
)


class GameManager:
    def __init__(self, player_ids: list[int]):
        players = [Player(id) for id in player_ids]
        # self.game: Game = Game.initialize(players, ranks=list(range(2, 8)))
        self.game = Game.initialize(players)
        print("game initialized")

    def get_private_infos(self, player_id: Optional[int] = None):
        return request_models.PrivateInfo(
            data=request_models.PlayerPrivateInfo.from_player(self.game.get_player(player_id))
        ).dict()

    def get_public_infos(self):
        return request_models.PublicInfo(
            data=request_models.PublicInfoData(
                game_id=self.game.game_id,
                play_pile=[vars(card) for card in self.game.play_pile.cards],
                game_state=self.game.state,
                nbr_of_cards_in_deck=len(self.game.deck),
                currents_turn=self.game.get_player().id_,
                player_public_info=[
                    request_models.PlayerPublicInfo.from_player(player)
                    for player in self.game.active_players
                ],
            )
        ).dict()

    def get_rules(self):
        return request_models.Rules().dict()

    def process_request(self, req: request_models.BaseRequest):
        player = self.game.get_player(req.player_id)
        print(player)
        if isinstance(req, request_models.ChoosePublicCardsRequest):
            self.game.process_choose_cards(ChoosePublicCardsRequest.from_dict(player, req.dict()))
        if isinstance(req, request_models.PrivateCardsRequest):
            self.game.process_playrequest(PrivateCardsRequest.from_dict(player, req.dict()))
        if isinstance(req, request_models.TakePlayPileRequest):
            self.game.process_playrequest(TakePlayPileRequest(player))
        if isinstance(req, request_models.HiddenCardRequest):
            self.game.process_hidden_card(HiddenCardRequest(player))
