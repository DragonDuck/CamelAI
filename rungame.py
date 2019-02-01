from bots import RandomBot
import camelup


def run_game():
    players = [RandomBot, RandomBot, RandomBot, RandomBot]
    for i in range(1000):
        game = camelup.play_game(players=players)


if __name__ == "__main__":
    run_game()
