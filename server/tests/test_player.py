from pyshithead import Card, Player


def test_player_initialization():
    player = Player(1)
    assert player.id == 1
    assert player.hidden_cards.is_empty() == True
    assert player.public_cards.is_empty() == True
    assert player.private_cards.is_empty() == True


def test_player_add_hidden_card(player: Player, card_2t: Card):
    player.hidden_cards.put([card_2t])
    assert player.hidden_cards.is_empty() == False
    assert player.public_cards.is_empty() == True
    assert player.private_cards.is_empty() == True
