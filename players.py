import random
import math


class PlayerInterface:
    """
    All bots must extend this interface and implement the method 'move()'.

    This function should return one of the following lists
        - [0]                               Roll the dice and randomly move a camel
        - [1, trap_type, trap_location]     Move trap to a given location.
                                                - trap_type: +1/-1 depending on whether
                                                  it adds or removes one from the roll
                                                - trap_location: ranges from 0 to board_size (exclusive)
        - [2, camel_id]                     Make round winner bet
                                                - camel_id: Camel ID
        - [3, bet_type, camel_id]           Make game winner or loser bet
                                                - bet_type: "win"/"lose" for winner/loser bet, respectively
                                                - camel_id: Camel ID

    Note that the game independently checks that moves are permissible but will
    raise exceptions if they are not. Your subclass must ensure that only valid
    movies are made. That means your code must check that:
    - traps should only be placed on valid squares
    - round winner bets on a camel can only be made if there are still betting
      cards available
    - game winner and loser bets on a camel can only be made once by each player

    The class GameState contains all necessary information to validate moves.

    Subclasses should remain stateless and the move()-function should be a
    static function as the game-code never instantiates any of the player
    classes.
    """
    @staticmethod
    def move(active_player, game_state):
        raise NotImplementedError(
            "Do not create an instance of the PlayerInterface! "
            "Extend this class and make sure to implement the move() function.")


class Player0(PlayerInterface):
    @staticmethod
    def move(active_player, game_state):
        # This dumb player always moves a camel
        return [0]


# class Player1(PlayerInterface):
#     def move(self, g):
#         # This player is less dumb. If they have the least amount of money they'll make a round winner bet
#         # If they aren't in last then they'll place a trap on a random square. Still p dumb though
#         if min(g.player_money_values) == g.player_money_values[player]:
#             return [2,random.randint(0,len(g.camels)-1)]
#         return [1,math.floor(2*random.random())*2-1,random.randint(1,10)]
#
# class Player2(PlayerInterface):
#     def move(player,g):
#         #This dumb player always makes a round winner bet
#         return [2,random.randint(0,len(g.camels)-1)]
