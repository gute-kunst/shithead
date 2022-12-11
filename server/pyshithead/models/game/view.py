from pyshithead.models.game import Game


class View:
    @staticmethod
    def show_game(game: Game):
        print("--- PUBLIC CARDS ---")
        for player in game.active_players.traverse_single():
            print(f"Player-{player.data.id_}: {player.data.public_cards}")
        print(f"TOP OF PLAY PILE: {game.play_pile.look_from_top(4)}")
        print(f"CARDS IN DECK: {len(game.deck)}")
        print("--------------------")
