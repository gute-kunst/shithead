import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from pyshithead import GAME_ID
from pyshithead.main import app, game_tables_manager
from pyshithead.models.common import GameManager, request_models
from pyshithead.models.game.errors import CardsNotInPlayersPrivateHandsError

from .models_game.conftest import *


@pytest.fixture
def client():
    with TestClient(app, base_url="http://localhost") as websocket_client:
        yield websocket_client


@pytest.fixture
def ws_before_joined(client):
    with client.websocket_connect(f"/game/{GAME_ID}") as a:
        with client.websocket_connect(f"/game/{GAME_ID}") as b:
            yield (a, b)


@pytest.fixture
def ws_on_joined(ws_before_joined):
    (a, b) = ws_before_joined
    for _ in range(5):
        a.receive_json()
    for _ in range(3):
        b.receive_json()

    yield (a, b)


@pytest.fixture
def game_choose_cards():
    players = [Player(0), Player(1)]
    deck = Dealer.provide_deck()
    Dealer.deal_cards_to_players(deck, players)
    return Game(players, deck, state=GameState.PLAYERS_CHOOSE_PUBLIC_CARDS)


@pytest.fixture
def game_manager_choose_cards(game_choose_cards):
    game_manager = GameManager(player_ids=[0, 1])
    game_manager.game = game_choose_cards
    return game_manager


@pytest.fixture
def game_first_move():
    players = [Player(0), Player(1)]
    deck = Dealer.provide_deck()
    Dealer.deal_cards_to_players(deck, players, put_public_to_private=False)
    return Game(players, deck, state=GameState.DURING_GAME)


@pytest.fixture
def game_manager_first_move(game_first_move):
    game_manager = GameManager(player_ids=[0, 1])
    game_manager.game = game_first_move
    return game_manager


def test_websocket_hello_world(client: TestClient):
    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_json()
        assert data == {"msg": "Hello WebSocket"}


def test_join_adds_client(client: TestClient):
    with client.websocket_connect(f"/game/{GAME_ID}") as websocket:
        data = websocket.receive_json()
        data_broadcast = websocket.receive_json()
        assert "client_id" in data
        nbr_clients = asyncio.run(
            game_tables_manager.get_game_table_by_id(GAME_ID)
        ).client_manager.nbr_of_clients()
        assert "A new player joined" in data_broadcast["message"]
        assert nbr_clients == 1
        assert (
            asyncio.run(game_tables_manager.get_game_table_by_id(GAME_ID))
            .client_manager.clients[0]
            .id_
            == data["client_id"]
        )


def test_join_two_clients(ws_before_joined):
    nbr_clients = asyncio.run(
        game_tables_manager.get_game_table_by_id(GAME_ID)
    ).client_manager.nbr_of_clients()
    assert nbr_clients == 2


def test_join_two_clients_server_response(ws_before_joined):
    (a, b) = ws_before_joined
    a_responses = []
    b_responses = []
    for _ in range(5):
        a_responses.append(a.receive_json())

    assert len([None for res in a_responses if res["type"] == "client_id"]) == 1
    assert len([None for res in a_responses if res["type"] == "current_game_table"]) == 2

    for _ in range(3):
        b_responses.append(b.receive_json())

    assert len([None for res in b_responses if res["type"] == "client_id"]) == 1
    assert len([None for res in b_responses if res["type"] == "current_game_table"]) == 1


def test_start_game(ws_on_joined):
    (a, b) = ws_on_joined
    a.send_json({"type": "start_game"})
    # RULES
    a_rules = a.receive_json()
    assert "rules" in a_rules.values()
    b_rules = b.receive_json()
    assert "rules" in b_rules.values()
    assert a_rules == b_rules
    # PUBLIC INFO
    a_pub_info = a.receive_json()
    assert "public_info" in a_pub_info.values()
    b_pub_info = b.receive_json()
    assert "public_info" in b_pub_info.values()
    assert a_pub_info == b_pub_info
    # PRIVATE INFO
    a_private_info = a.receive_json()
    assert "private_info" in a_private_info.values()
    b_private_info = b.receive_json()
    assert "private_info" in b_private_info.values()
    assert a_private_info != b_private_info


def test_start_game_deterministic(ws_on_joined, game_with_two_players_during_game_empty_playpile):
    (a, b) = ws_on_joined
    a.send_json({"type": "start_game"})
    # RULES
    a_rules = a.receive_json()
    assert "rules" in a_rules.values()
    game_manager = game_tables_manager.game_tables[0].game_manager
    mocked_game = game_with_two_players_during_game_empty_playpile
    game_manager.game = mocked_game
    b_rules = b.receive_json()
    assert "rules" in b_rules.values()
    assert a_rules == b_rules
    # PUBLIC INFO
    a_pub_info = a.receive_json()
    assert "public_info" in a_pub_info.values()
    b_pub_info = b.receive_json()
    assert "public_info" in b_pub_info.values()
    assert a_pub_info == b_pub_info
    # PRIVATE INFO
    a_private_info = a.receive_json()
    assert "private_info" in a_private_info.values()
    b_private_info = b.receive_json()
    assert "private_info" in b_private_info.values()
    assert a_private_info != b_private_info


def test_choose_cards(ws_on_joined, game_manager_choose_cards: GameManager):
    (a, b) = ws_on_joined
    game_tables_manager.game_tables[0].game_manager = game_manager_choose_cards
    private_cards_a = list(game_manager_choose_cards.game.get_player(0).private_cards)
    a.send_json(
        request_models.ChoosePublicCardsRequest(
            player_id=0,
            cards=[request_models.CardModel(**vars(card)) for card in private_cards_a[:3]],
        ).dict()
    )
    a_pub_info = a.receive_json()
    a_private_info = a.receive_json()
    assert len(a_private_info["data"]["private_cards"]) == 3
    assert len(a_pub_info["data"]["player_public_info"][0]["public_cards"]) == 3
    b_pub_info = b.receive_json()
    assert a_pub_info == b_pub_info
    assert a_pub_info["data"]["game_state"] == GameState.PLAYERS_CHOOSE_PUBLIC_CARDS
    private_cards_b = list(
        game_tables_manager.game_tables[0].game_manager.game.get_player(1).private_cards
    )
    b.send_json(
        request_models.ChoosePublicCardsRequest(
            player_id=1,
            cards=[request_models.CardModel(**vars(card)) for card in private_cards_b[:3]],
        ).dict()
    )
    b_pub_info_2 = b.receive_json()
    b_private_info_2 = b.receive_json()
    a_pub_info_2 = a.receive_json()
    assert a_pub_info_2["data"]["game_state"] == GameState.DURING_GAME
    assert b_pub_info_2 == a_pub_info_2


def test_first_play_request(ws_on_joined, game_manager_first_move: GameManager):
    (a, b) = ws_on_joined
    game_tables_manager.game_tables[0].game_manager = game_manager_first_move
    card_to_play = sorted(
        list(game_manager_first_move.game.get_player(0).private_cards), key=lambda card: card.rank
    )[0]
    a.send_json(
        request_models.PrivateCardsRequest(
            player_id=0, cards=[request_models.CardModel(**vars(card_to_play))]
        ).dict()
    )

    b_pub_info = b.receive_json()
    assert b_pub_info["data"]["currents_turn"] == 1
    assert b_pub_info["data"]["play_pile"] == [vars(card_to_play)]
    a_pub_info = a.receive_json()
    a_private_info = a.receive_json()
    assert vars(card_to_play) not in a_private_info["data"]["private_cards"]


def test_invalid_play_request(ws_on_joined, game_manager_first_move: GameManager, card_2c):
    (a, b) = ws_on_joined
    game_tables_manager.game_tables[0].game_manager = game_manager_first_move
    card_not_in_hand = card_2c
    private_cards = list(game_manager_first_move.game.get_player(0).private_cards)
    assert card_not_in_hand not in private_cards
    a.send_json(
        request_models.PrivateCardsRequest(
            player_id=0, cards=[request_models.CardModel(**vars(card_not_in_hand))]
        ).dict()
    )
    a_private_info = a.receive_json()
    assert a_private_info["type"] == "invalid-request"
    assert a_private_info["data"] == CardsNotInPlayersPrivateHandsError().message
