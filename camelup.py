import random
import copy
import uuid
import hashlib
# import math
from players import PlayerInterface, Player0


class GameState:
    def __init__(self, num_camels=5, num_players=4, board_size=16,
                 first_place_round_payout=(5, 3, 2),
                 second_place_round_payout=(1, 1, 1),
                 third_or_worse_place_round_payout=(-1, -1, -1),
                 game_end_payout=(8, 5, 3, 1)):

        # Global game variables
        self.NUM_CAMELS = num_camels
        self.CAMELS = ["c_" + str(i) for i in range(num_camels)]
        self.NUM_PLAYERS = num_players
        self.BOARD_SIZE = board_size

        # Payout structures
        if not len(first_place_round_payout) == \
                len(second_place_round_payout) == \
                len(third_or_worse_place_round_payout):
            raise ValueError("Round payouts must all have the same length")

        self.FIRST_PLACE_ROUND_PAYOUT = first_place_round_payout
        self.SECOND_PLACE_ROUND_PAYOUT = second_place_round_payout
        self.THIRD_OR_WORSE_PLACE_ROUND_PAYOUT = third_or_worse_place_round_payout
        self.GAME_END_PAYOUT = game_end_payout

        # Game state variables
        # Each entry indicates the order of camels on that fields
        # The list is twice as long as the actual track to allow camels to pass the finish line by variable distances
        self.camel_track = [[] for _ in range(board_size * 2)]
        self.trap_track = [[] for _ in range(board_size * 2)]  # entry of the form [trap_type (-1,1), player]
        self.player_has_placed_trap = [False] * num_players
        self.round_bets = []  # entries of the form [camel, player]
        self.game_winner_bets = []  # entries of the form [camel, player]
        self.game_loser_bets = []  # entries of the form [camel, player]
        self.player_money_values = [2] * num_players
        self.camel_yet_to_move = [True] * num_camels
        self.active_game = True  # Has one of the camels passed the finish line?
        self.game_winner = []

        # Initialize camels in random position
        initial_camels = copy.deepcopy(self.CAMELS)
        for _ in range(0, num_camels):
            index = random.randint(0, len(initial_camels) - 1)
            distance = roll_dice() - 1
            self.camel_track[distance].append(initial_camels[index])
            initial_camels.remove(initial_camels[index])

    def __setattr__(self, key, value):
        """
        This overwritten function prevents changing global parameters once they've been set. Note that this is a
        development help more than an actual security measure as there are ways to circumvent this.
        :param key:
        :param value:
        :return:
        """
        if key.isupper() and key in self.__dict__:
            raise TypeError("Game constants cannot be changed")
        else:
            self.__dict__[key] = value

    def get_player_bets(self, player):
        """
        This function lists all the camels a player has bet on for game winner/loser
        :return:
        """
        return [entry[0] for entry in self.game_winner_bets + self.game_loser_bets if entry[1] == player]


def get_valid_moves(g, player):
    """
    This is the "rules engine" that checks for valid moves. It returns a list of lists with elements in one of the
    following formats:
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
    :param g: GameState object
    :param player:
    :return:
    """
    valid_moves = []

    # Check if a camel can still be moved. Note that this should ALWAYS be the case. If the last camel moves then the
    # end of round should be triggered after the move. This check is a failsafe and will result in an exception on
    # purpose
    if sum(g.camel_yet_to_move) == 0:
        raise RuntimeError("All camels have moved but end of round was not triggered!")
    valid_moves.append((0,))

    # Traps can be placed anywhere where there is no camel or trap. They may also not be adjacent to a trap UNLESS
    # the player is moving his trap to an adjacent spot. They may also not be placed on the first spot of the track.
    trap_track_without_player_trap = [entry if len(entry) > 0 and entry[1] != player else [] for entry in g.trap_track]
    valid_trap_locations = [
        i for i in range(1, g.BOARD_SIZE) if
        len(g.camel_track[i]) == 0 and  # Cannot be placed under camels
        len(g.trap_track[i]) == 0 and  # Cannot be placed on other trap
        len(trap_track_without_player_trap[i - 1]) == 0 and  # Cannot be placed next to another player's trap
        len(trap_track_without_player_trap[i + 1]) == 0]  # Cannot be placed next to another player's trap
    valid_moves += [(1, trap_type, trap_location) for trap_type in (1, -1) for trap_location in valid_trap_locations]

    # Round winner bets can be made as long as there are still cards available
    for camel in g.CAMELS:
        if len([bet for bet in g.round_bets if len(bet) > 0 and bet[0] == camel]) < len(g.FIRST_PLACE_ROUND_PAYOUT):
            valid_moves.append((2, camel))

    # Game winner/loser bets can be made as long as the player hasn't already bet on that camel
    # valid_moves += [(bet_type, camel) for bet_type in ("win", "lose")
    #                 for camel in [camel for camel in g.CAMELS if camel not in g.player_game_bets[player]]]
    valid_moves += [(3, bet_type, camel) for bet_type in ("win", "lose")
                    for camel in g.CAMELS if camel not in g.get_player_bets(player)]

    return valid_moves


def roll_dice():
    """
    Customizable dice roll logic
    :return:
    """
    return random.randint(1, 3)


def print_update(msg, display_updates=True):
    """
    A helper function to reduce boilerplate code
    :param msg:
    :param display_updates:
    :return:
    """
    if display_updates:
        print(msg)
    return None


def play_game(players):
    """
    Play a game until a camel wins. The game loops through players and calls their move() function until a camel passes
    the finish line.
    :param players: A list of instances of player classes that extend PlayerInterface
    :return:
    """

    # Check that player instances are valid objects
    if not all([issubclass(player, PlayerInterface) for player in players]):
        raise ValueError("All players must extend PlayerInterface")

    players = [player.move for player in players]

    def action(result, player):
        print_update("Player Action: " + str(result))
        if result[0] == 0:  # Player wants to move camel
            print_update("Player " + str(player) + " moves a camel")
            move_camel(g, player)
        elif result[0] == 1:  # Player wants to place trap
            print_update("Player " + str(player) + " places or moves a trap")
            move_trap(g, result[1], result[2], player)
        elif result[0] == 2:  # Player wants to make round winner bet
            print_update("Player " + str(player) + " makaes a round winner bet")
            place_round_winner_bet(g, result[1], player)
        elif result[0] == 3:  # Player wants to make game winner bet
            print_update("Player " + str(player) + " makes a game winner bet")
            place_game_winner_bet(g, result[1], player)
        elif result[0] == 4:  # Player wants to make game loser bet
            print_update("Player " + str(player) + " makes a game loser bet")
            place_game_loser_bet(g, result[1], player)
        else:
            raise ValueError("Illegal action ({}) performed by player {}".format(result, player))
        return

    g = GameState()
    g_round = 0
    while g.active_game:
        active_player = (g_round % len(players))
        action(players[active_player](active_player, copy.deepcopy(g)), active_player)
        g_round += 1
        display_game_state(g)
    print_update("$ Totals:")
    print_update("\t" + str(g.player_money_values))
    print_update("Winner: " + str(g.game_winner))
    return g.game_winner


def move_camel(g, player):
    """
    Selects a random camel and moves it according to the roll_dice() function.
    This function adheres to rules regarding camel stacking and bevavior at traps
    :param g:
    :param player:
    :return:
    """
    # Select a random camel to move
    camel_index = random.choice([i for i in range(num_camels) if g.camel_yet_to_move[i]])

    # Remove camel from pool
    g.camel_yet_to_move[camel_index] = False

    # Find current position of camel on board and in camel stack
    [curr_pos, found_y_pos] = [
        (ix, iy) for ix, row in enumerate(g.camel_track) for iy, i in enumerate(row)
        if i == g.camels[camel_index]][0]
    stack = len(g.camel_track[curr_pos]) - found_y_pos

    # Roll the dice
    distance = roll_dice()

    # Check if camel hits a trap
    stack_from_bottom = False
    if len(g.trap_track[curr_pos + distance]) > 0:
        print_update("Player hit a trap!")
        if g.trap_track[curr_pos + distance][0] == -1:
            stack_from_bottom = True
        g.player_money_values[g.trap_track[curr_pos + distance][1]] += 1  # Give the player who set the trap a coin
        distance += g.trap_track[curr_pos + distance][0]  # Change the distance according to trap

    camels_to_move = []

    # If a camel hits a -1 trap, the stack is inverted
    # TODO: Write a test case for this to ensure that this actually works
    if stack_from_bottom:  # stack from bottom if trap was -1
        for c in range(0, stack):
            camels_to_move.append(g.camel_track[curr_pos].pop(stack - c - 1))
            g.camel_track[curr_pos + distance].insert(0, camels_to_move[0])
            camels_to_move.clear()
    else:  # Stack normally
        for c in range(0, stack):
            camels_to_move.append(g.camel_track[curr_pos].pop(found_y_pos))
            g.camel_track[curr_pos + distance].append(camels_to_move[0])
            camels_to_move.clear()
    g.player_money_values[player] += 1  # Give the rolling player a coin

    # If round is over, trigger End Of Round effects
    if sum(g.camel_yet_to_move) == 0:
        end_of_round(g)

    if len(g.camel_track[board_size]) + len(g.camel_track[board_size + 1]) + len(g.camel_track[board_size + 2]) > 0:
        end_of_round(g)
        end_of_game(g)  # If game is over, trigger End Of Game and round effects

    return True


def move_trap(g, trap_type, trap_place, player):
    """
    Places, or moves, a player's trap. Automatically decides whether to place or move the trap based on whether the
    player has already placed his trap. This function checks that the spot is legal, i.e. not occupied by a trap or
    camel and not next to a trap.
    :param g:
    :param trap_type:
    :param trap_place:
    :param player:
    :return:
    """
    # TODO: Ask Zach: Can I remove a trap as a move?
    # TODO: No
    # Check if player has places the trap and remove it if so
    if g.player_has_placed_trap[player]:
        # Remove trap
        # Find old trap position
        [curr_pos] = [[y, row[0]] for y, row in enumerate(g.trap_track) if (row[1] if 0 < len(row) else None) == player]

        # Check that the old position/type and the new position/type aren't identical
        if (curr_pos[0] == trap_place) and (curr_pos[1] == trap_type):
            raise ValueError("Old and new trap position/type are identical")

        g.trap_track[curr_pos[0]] = []
        g.player_has_placed_trap[player] = False

    # Place trap in new position
    # Check that trap_place and trap_type are legal
    if (trap_place < 0) or (trap_place > g.BOARD_SIZE):
        raise ValueError("Illegal value for trap_place")
    if trap_type not in (1, -1):
        raise ValueError("Illegal value for trap_type")

    # Check that spot isn't occupied by a camel
    if len(g.camel_track[trap_place]) != 0:
        raise ValueError("trap_place occupied by camel")

    # Check that spot isn't occupied by or next to an existing trap
    if (len(g.trap_track[trap_place - 1]) != 0) or \
       (len(g.trap_track[trap_place]) != 0) or \
       (len(g.trap_track[trap_place + 1]) != 0):
        raise ValueError("trap_place occupied by or next to an existing trap")

    g.trap_track[trap_place] = [trap_type, player]
    g.player_has_placed_trap[player] = True
    return True


def place_game_winner_bet(g, camel, player):
    # Check to see if they are betting on a camel they've already bet on
    for i in range(0, len(g.player_game_bets[player])):
        if check_bet(g.player_game_bets[player][i], str(camel)):
            print_update(str(player) + ' tried to bet on a camel winning that they\'d already bet on!')
            return False
    g.game_winner_bets.append([hash_bet(str(camel)), player])
    g.player_game_bets[player].append(hash_bet(str(camel)))
    return True


def place_game_loser_bet(g, camel, player):
    # Check to see if they are betting on a camel they've already bet on
    for i in range(0, len(g.player_game_bets[player])):
        if check_bet(g.player_game_bets[player][i], str(camel)):
            print_update(str(player) + ' tried to bet on a camel winning that they\'d already bet on!')
            return False
    g.game_loser_bets.append([hash_bet(str(camel)), player])
    g.player_game_bets[player].append(hash_bet(str(camel)))
    return True


def place_round_winner_bet(g, camel, player):
    # TODO: There needs to be a check here that only the permitted bets are taken
    g.round_bets.append([camel, player])
    return True


def end_of_round(g):
    first_place_payout_index = 0
    second_place_payout_index = 0
    third_or_worse_place_payout_index = 0

    first_place_camel = find_camel_in_nth_place(g.camel_track, 1)
    second_place_camel = find_camel_in_nth_place(g.camel_track, 2)

    for i in range(0, len(g.round_bets) - 1):  # Payout
        if g.round_bets[i][0] == first_place_camel:
            payout = (first_place_round_payout[first_place_payout_index] if first_place_payout_index < len(
                first_place_round_payout) else 0)
            g.player_money_values[g.round_bets[i][1]] += payout  # handles out of range exceptions by returning 0
            print_update(
                "Paid Player " + str(g.round_bets[i][1]) + " " + str(payout) + " coins for selecting the round winner")
            first_place_payout_index += 1
        elif g.round_bets[i][0] == second_place_camel:
            payout = (second_place_round_payout[second_place_payout_index] if second_place_payout_index < len(
                second_place_round_payout) else 0)
            g.player_money_values[g.round_bets[i][1]] += payout  # handles out of range exceptions by returning 0
            second_place_payout_index += 1
            print_update("Paid Player " + str(g.round_bets[i][1]) + " " + str(
                second_place_round_payout) + " coins for selecting the round runner up")
        else:
            payout = (third_or_worse_place_round_payout[
                          third_or_worse_place_payout_index] if third_or_worse_place_payout_index < len(
                third_or_worse_place_round_payout) else 0)
            g.player_money_values[g.round_bets[i][1]] += payout  # handles out of range exceptions by returning 0
            third_or_worse_place_payout_index += 1
            print_update("Paid Player " + str(g.round_bets[i][1]) + " " + str(
                third_or_worse_place_round_payout) + " coins for selecting the a third place or worse camel")

    # Prepare GameState for the beginning of next round
    g.camel_yet_to_move = [True, True, True, True, True]
    g.round_bets = []  # clear round bets
    # TODO: Check with Zach if traps are reset after each round
    # TODO: Yes
    # g.trap_track = [[] for i in range(finish_line)]
    # g.player_has_placed_trap = [False, False, False, False]
    return


def end_of_game(g):
    winning_camel = find_camel_in_nth_place(g.camel_track, 1)  # Find camel that won
    losing_camel = find_camel_in_nth_place(g.camel_track, num_camels)  # Find camel that lost

    # Settle game bets
    # game_bets are of the form [camel,player]
    # Selecting correct winner gives 8,5,3,1,1,1,1
    # Selecting wrong gives -1
    def get_payout(pind):
        return game_end_payout[pind] if pind < len(game_end_payout) else 1

    # Settle bets on winning camel
    payout_index = 0
    for i in range(0, len(g.game_winner_bets) - 1):
        if check_bet(g.game_winner_bets[i][0], str(winning_camel)):  # if you win, get prize
            payout = get_payout(payout_index)
            g.player_money_values[g.game_winner_bets[i][1]] += payout
            print_update(
                "Paid Player " + str(g.game_winner_bets[i][1]) + " " +
                str(payout) + " coins for selecting the game winner")
            payout_index += 1  # decrease value of guessing winning camel
        else:
            g.player_money_values[g.game_winner_bets[i][1]] -= 1
            print_update(
                "Paid Player " + str(g.game_winner_bets[i][1]) + " -1 coins for incorrectly selecting the game winner")

    # Settle bets on losing camel
    payout_index = 0
    for i in range(0, len(g.game_loser_bets) - 1):
        if check_bet(g.game_loser_bets[i][0], str(losing_camel)):  # if you win, get prize
            payout = get_payout(payout_index)
            g.player_money_values[g.game_loser_bets[i][1]] += payout
            print_update(
                "Paid Player " + str(g.game_loser_bets[i][1]) + " " + " coins for selecting the game loser")
            payout_index += 1  # decrease value of guessing winning camel
        else:
            g.player_money_values[g.game_loser_bets[i][1]] -= 1
            print_update(
                "Paid Player " + str(g.game_loser_bets[i][1]) + " -1 coins for incorrectly selecting the game loser")

    g.active_game = False
    g.game_winner = [i for i, j in enumerate(g.player_money_values) if j == max(g.player_money_values)]
    return True


def find_camel_in_nth_place(track, n):
    if n > num_camels or n < 1:
        raise ValueError('Something tried to find a camel in a Nth place, where N is out of bounds')
    found_camel = False
    camels_counted = 0
    i = 1
    while not found_camel:
        dtg = n - camels_counted
        camels_in_stack = len(track[len(track) - i])
        if camels_in_stack >= dtg:
            return track[len(track) - i][camels_in_stack - dtg]
        else:
            camels_counted += camels_in_stack
            i += 1
    return False


def display_game_state(g, display_updates=True):
    if display_updates:
        print("Track:")
        display_track_state(g.camel_track)
        print("\n")
        print("Traps:")
        display_track_state(g.trap_track)
        print("\n")
        print("$ Totals:")
        print("\t" + str(g.player_money_values))
        print("\n")


def display_track_state(track, display_updates=True):
    if not display_updates:
        return None

    max_stack = len(max(track, key=len))

    # Print milestones
    track_label_string = "\t|"
    for _ in range(0, board_size):
        track_label_string += ("-" + str(_) + "-|")
    print(track_label_string)

    # Print blank line
    track_label_string = "\t"
    for i in range(0, board_size):
        track_label_string += ("---" + "-" * len(str(i)))
    print(track_label_string + "-")

    # Print N/A if there are no objects (camels/traps)
    if max_stack == 0:
        track_label_string = "\t  "  # extra spaces because double digit numbers mess things up
        for _ in range(0, board_size):
            track_label_string += "  "
        print(track_label_string + "NA")

    # otherwise print those objects
    for stack_spot in range(0, max_stack):
        track_string = "\t"
        for track_spot in range(0, board_size):
            if len(track[track_spot]) >= max_stack - stack_spot:
                str_len = len(str(track[track_spot][max_stack - stack_spot - 1]))
                track_string += (
                        "|" + " " * (2 - str_len) + str(track[track_spot][max_stack - stack_spot - 1]) +
                        " " * len(str(track_spot)))
            else:
                track_string += ("|" + " " * (2 + len(str(track_spot))))
        print(track_string + "|")

    # Print blank line again
    track_label_string = "\t"
    for i in range(0, board_size):
        track_label_string += ("---" + "-" * len(str(i)))
    print(track_label_string + "-")
    # Print milestones again

    track_label_string = "\t|"
    for _ in range(0, board_size):
        track_label_string += ("-" + str(_) + "-|")
    print(track_label_string)


def hash_bet(bet):
    # uuid is used to generate a random number
    salt = uuid.uuid4().hex
    return hashlib.sha256(salt.encode() + bet.encode()).hexdigest() + ':' + salt


def check_bet(hashed_bet, user_bet):
    bet, salt = hashed_bet.split(':')
    return bet == hashlib.sha256(salt.encode() + user_bet.encode()).hexdigest()


def test_game():
    """
    This is just a demo function
    :return:
    """
    players = [Player0, Player0, Player0, Player0]
    # player_points = [0 for i in range(len(player_pool))]
    # print(play_game(players))

    for game in range(10000):
        winner = play_game(players)
