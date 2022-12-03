from pyshithead import Game


class View:
    @staticmethod
    def show_game(game: Game):
        print("--- PUBLIC CARDS ---")
        for player in game.active_players.traverse_single():
            print(f"Player-{player.data.id_}: {player.data.public_cards}")
        print("--- TOP OF PLAY PILE ---")
        print(game.play_pile.look_from_top(1))
        print("--------------------")
