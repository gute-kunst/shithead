from pyshithead import Card, Player


def test_player_initialization():
    player = Player(1)
    assert player.id_ == 1
    assert player.hidden_cards.is_empty() is True
    assert player.public_cards.is_empty() is True
    assert player.private_cards.is_empty() is True


def test_player_add_hidden_card(player: Player, card_2t: Card):
    player.hidden_cards.put([card_2t])
    assert player.hidden_cards.is_empty() is False
    assert player.public_cards.is_empty() is True
    assert player.private_cards.is_empty() is True


def test_player_eligible_play_hidden_card(player_initialized: Player):
    assert player_initialized.eligible_play_hidden_card() is False
    player_initialized.private_cards.cards.clear()
    assert player_initialized.eligible_play_hidden_card() is False
    player_initialized.public_cards.cards.clear()
    assert player_initialized.eligible_play_hidden_card() is True


def test_player_compare_true():
    p1 = Player(1)
    p1_ = Player(1)
    assert p1 == p1_


def test_player_compare_false():
    p1 = Player(1)
    p2 = Player(2)
    assert p1 != p2
