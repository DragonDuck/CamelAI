import pandas as pd
import os
import sys
import camelup
import bots


def run_game(num_games, players):
    """
    Simulate Camel Up games with the given list of player bots
    :param num_games: An integer
    :param players: A list of classes inheriting PlayerInterface
    :return:
    """

    for i in range(num_games):
        if i % 100 == 0:
            print("Simulating game {} out of {}".format(i, num_games))
        game, gamestate = camelup.play_game(players=players)
        game = pd.DataFrame(game)
        game.to_csv(path_or_buf=os.path.join("game_logs", "game_{}.csv".format(i)))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise ValueError(
            "Usage: python {} <NUM_GAMES> <PLAYER_1> ... <PLAYER_N>\n".format(sys.argv[0]) +
            "PLAYER_J should be the name of a bot class to be imported from bots.py\n" +
            "The game can technically run with a single player")

    ng = None
    try:
        ng = int(sys.argv[1])
    except ValueError:
        print("NUM_GAMES must be an integer")

    p = []
    for botname in sys.argv[2:]:
        p.append(getattr(bots, botname))

    print("Simulating {} games  with {} players: {}...".format(ng, len(p), str(p)))
    run_game(num_games=ng, players=p)
