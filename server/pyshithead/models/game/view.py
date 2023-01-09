class View:
    @staticmethod
    def show_public_info(public_info: dict):
        print("--- PUBLIC CARDS ---")
        for player in public_info["player_public_info"]:
            print(f"Player-{player['id']}: {player['public_cards']}")
        print(f"TOP OF PLAY PILE: {public_info['play_pile']}")
        print(f"CARDS IN DECK: {public_info['nbr_of_cards_in_deck']}")
        print("--------------------")
