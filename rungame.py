from bots import RandomBot
import pandas as pd
import os
import camelup


def run_game():
    players = [RandomBot, RandomBot, RandomBot, RandomBot]
    for i in range(10):
        game = camelup.play_game(players=players)
        game = pd.DataFrame(game)
        game.to_csv(path_or_buf=os.path.join("game_logs", "game_{}.csv".format(i)))


if __name__ == "__main__":
    run_game()
