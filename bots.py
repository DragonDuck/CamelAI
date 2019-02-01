from playerinterface import PlayerInterface
from camelup import get_valid_moves
# from actionids import GAME_BET_ACTION_ID, ROUND_BET_ACTION_ID, MOVE_TRAP_ACTION_ID, MOVE_CAMEL_ACTION_ID
import random


class RandomBot(PlayerInterface):
    """
    This bot randomly choses a move to make. It chooses in a hierarchical fashion, i.e.
    1. Identify which types of moves are available
    2. Choose a type of move, i.e. move camel, place trap, make a game bet, or make a round bet
    3. Randomly select the specific variant of the move to perform, e.g. where to place the trap and what kind it
       should be.
    """
    @staticmethod
    def move(active_player, game_state):
        valid_moves = get_valid_moves(g=game_state, player=active_player)
        valid_super_moves = tuple(set([move[0] for move in valid_moves]))
        random_super_move = random.choice(valid_super_moves)
        possible_moves = [move for move in valid_moves if move[0] == random_super_move]
        return random.choice(possible_moves)
