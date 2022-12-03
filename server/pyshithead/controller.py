from pyshithead import (
    Card,
    Choice,
    ChoosePublicCardsRequest,
    Game,
    Player,
    PrivateCardsRequest,
    SpecialRank,
    View,
)


class Controller:
    def __init__(self, view=None):
        self.view = view
        self.gamemodel: Game = None

    def start(self):
        nbr_of_players = int(input("Nbr of players: "))
        players = [Player(id) for id in range(0, nbr_of_players)]
        self.game = Game(players)
        print("game initialized")
        print(self.game)
        for player in self.game.active_players.traverse_single():
            print(f"Select public cards for player {player.data.id_} ... ")
            private_cards = list(player.data.private_cards)
            print(f"Your Cards: {private_cards} \n")
            selection = []
            selection.append(int(input("Select first card [0,5]: ")))
            selection.append(int(input("Select second card [0,5]: ")))
            selection.append(int(input("Select third card [0,5]: ")))
            chosen_cards = [private_cards[select] for select in selection]
            req = ChoosePublicCardsRequest(player.data, chosen_cards)
            self.game.process_playrequest(req)
        View.show_game(self.game)
        while -1:
            player = self.game.get_player()
            print(f"Player: {player.id_} - select one card to play")
            private_cards = list(player.private_cards)
            print(private_cards)
            selection = int(input(f"Select card [0,{len(private_cards)-1}]: "))
            card: Card = private_cards[selection]
            choice = None
            if card.rank == SpecialRank.HIGHLOW:
                highlow = input("You played the Higher-Lower Card. Please type either 'H' or 'L'")

                if highlow == "H":
                    choice = Choice.HIGHER
                elif highlow == "L":
                    choice = Choice.LOWER
            req = PrivateCardsRequest(player, [card], choice)
            self.game.process_playrequest(req)
            View.show_game(self.game)

        print("done")


if __name__ == "__main__":
    print("Shithead Game")
    controller = Controller()
    controller.start()
