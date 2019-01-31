import random
import copy
from players import PlayerInterface

# Static parameters
# These are here to avoid "magic numbers" in the code. They can hypotheticall be changed but this will have no impact
# on the program logic.
__MOVE_CAMEL_ACTION_ID = 0
__MOVE_TRAP_ACTION_ID = 1
__ROUND_BET_ACTION_ID = 2
__GAME_BET_ACTION_ID = 3


class GameState:
    def __init__(self, num_camels=5, num_players=4, board_size=16,
                 first_place_round_payout=(5, 3, 2),
                 second_place_round_payout=(1, 1, 1),
                 third_or_worse_place_round_payout=-1,
                 game_end_payout=(8, 5, 3),
                 bad_game_end_bet=-1,
                 verbose=True):

        # Global game variables
        self.NUM_CAMELS = num_camels
        self.CAMELS = ["c_" + str(i) for i in range(num_camels)]
        self.NUM_PLAYERS = num_players
        self.BOARD_SIZE = board_size

        # Payout structures
        if not len(first_place_round_payout) == len(second_place_round_payout):
            raise ValueError("Round payouts must all have the same length")

        self.FIRST_PLACE_ROUND_PAYOUT = first_place_round_payout
        self.SECOND_PLACE_ROUND_PAYOUT = second_place_round_payout
        self.THIRD_OR_WORSE_PLACE_ROUND_PAYOUT = third_or_worse_place_round_payout
        self.GAME_END_PAYOUT = game_end_payout
        self.BAD_GAME_END_BET = bad_game_end_bet

        # Game parameter that can be changed
        self.verbose = verbose

        # Game state variables
        # Each entry indicates the order of camels on that fields
        # The list is twice as long as the actual track to allow camels to pass the finish line by variable distances
        self.camel_track = [[] for _ in range(board_size * 2)]
        self.trap_track = [[] for _ in range(board_size * 2)]  # entry of the form [trap_type (-1,1), player]
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

    def has_player_placed_trap(self, player):
        """
        Tests whether a player has already placed their trap
        :param player:
        :return:
        """
        player_trap = [entry for entry in self.trap_track if len(entry) > 0 and entry[1] == player]
        return True if len(player_trap) > 0 else False

    def get_game_bets_payout(self, index):
        """
        The payout for game winner/loser bets is 1 for any player who isn't in the first three to bet on the
        corresponding camel. This function helps generate the correct value for a given player index
        :param index: The bet index, i.e. index=4 for the 4th player to bet on the game winner/loser
        :return:
        """
        if index < len(self.GAME_END_PAYOUT):
            return self.GAME_END_PAYOUT[index]
        else:
            return 1


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
    valid_moves.append((__MOVE_CAMEL_ACTION_ID,))

    # Traps can be placed anywhere where there is no camel or trap. They may also not be adjacent to a trap UNLESS
    # the player is moving his trap to an adjacent spot. They may also not be placed on the first spot of the track.
    trap_track_without_player_trap = [entry if len(entry) > 0 and entry[1] != player else [] for entry in g.trap_track]
    valid_trap_locations = [
        i for i in range(1, g.BOARD_SIZE) if
        len(g.camel_track[i]) == 0 and  # Cannot be placed under camels
        len(g.trap_track[i]) == 0 and  # Cannot be placed on other trap
        len(trap_track_without_player_trap[i - 1]) == 0 and  # Cannot be placed next to another player's trap
        len(trap_track_without_player_trap[i + 1]) == 0]  # Cannot be placed next to another player's trap
    valid_moves += [(__MOVE_TRAP_ACTION_ID, trap_type, trap_location) for trap_type
                    in (1, -1) for trap_location in valid_trap_locations]

    # Round winner bets can be made as long as there are still cards available
    for camel in g.CAMELS:
        if len([bet for bet in g.round_bets if len(bet) > 0 and bet[0] == camel]) < len(g.FIRST_PLACE_ROUND_PAYOUT):
            valid_moves.append((__ROUND_BET_ACTION_ID, camel))

    # Game winner/loser bets can be made as long as the player hasn't already bet on that camel
    # valid_moves += [(bet_type, camel) for bet_type in ("win", "lose")
    #                 for camel in [camel for camel in g.CAMELS if camel not in g.player_game_bets[player]]]
    valid_moves += [(__GAME_BET_ACTION_ID, bet_type, camel) for bet_type in ("win", "lose")
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

    def action(result, player):
        if result[0] == 0:  # Player wants to move camel
            camel, distance = move_camel(g, player)
            print_update(
                msg="Player {} moves camel {} by {} spaces".format(str(player), camel, str(distance)),
                display_updates=g.verbose)
        elif result[0] == 1:  # Player wants to place trap
            move_trap(g, result[1], result[2], player)
            print_update(
                msg="Player {} moves a {:+d} trap to field {}".format(str(player), result[1], str(result[2])),
                display_updates=g.verbose)
        elif result[0] == 2:  # Player wants to make round winner bet
            place_round_winner_bet(g, result[1], player)
            print_update(
                msg="Player {} places a round winner bet on camel {}".format(str(player), result[1]),
                display_updates=g.verbose)
        elif result[0] == 3:  # Player wants to make game winner bet
            place_game_bet(g, result[1], result[2], player)
            print_update(
                msg="Player {} places a game '{}' bet on camel {}".format(str(player), result[1], result[2]),
                display_updates=g.verbose)
        else:
            raise ValueError("Illegal action ({}) performed by player {}".format(result, player))
        return

    g = GameState()
    g_round = 0
    while g.active_game:
        active_player = (g_round % len(players))
        action(
            result=players[active_player].move(active_player, copy.deepcopy(g)),
            player=active_player)
        g_round += 1
        display_game_state(g)
    print_update("$ Totals:", display_updates=g.verbose)
    print_update("\t" + str(g.player_money_values), display_updates=g.verbose)
    print_update("Winner: " + str(g.game_winner), display_updates=g.verbose)
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
    camel_index = random.choice([i for i in range(g.NUM_CAMELS) if g.camel_yet_to_move[i]])

    # Remove camel from pool
    g.camel_yet_to_move[camel_index] = False

    # Find current position of camel on board and in camel stack
    [curr_pos, found_y_pos] = [
        (ix, iy) for ix, row in enumerate(g.camel_track) for iy, i in enumerate(row)
        if i == g.CAMELS[camel_index]][0]

    # Roll the dice
    distance = roll_dice()

    # Check if camel hits a trap
    stack_from_bottom = False
    if len(g.trap_track[curr_pos + distance]) > 0:
        print_update("Player hit a trap!", display_updates=g.verbose)
        if g.trap_track[curr_pos + distance][0] == -1:
            stack_from_bottom = True
        g.player_money_values[g.trap_track[curr_pos + distance][1]] += 1  # Give the player who set the trap a coin
        distance += g.trap_track[curr_pos + distance][0]  # Change the distance according to trap

    # Move camels. If a camel hits a -1 trap, the stack is inverted
    camels_to_move = g.camel_track[curr_pos][found_y_pos:]
    g.camel_track[curr_pos] = g.camel_track[curr_pos][0:found_y_pos]
    if stack_from_bottom:
        g.camel_track[curr_pos + distance] = camels_to_move + g.camel_track[curr_pos + distance]
    else:
        g.camel_track[curr_pos + distance] = g.camel_track[curr_pos + distance] + camels_to_move

    # Give the rolling player a coin
    g.player_money_values[player] += 1

    # Print update
    print_update(
        msg="Player {} moves camel {} by {} spaces".format(str(player), g.CAMELS[camel_index], str(distance)),
        display_updates=g.verbose)

    # If round is over, trigger End Of Round effects
    end_of_round_scored = False
    if sum(g.camel_yet_to_move) == 0:
        end_of_round(g)
        end_of_round_scored = True

    # If game is over, trigger End Of Game and round effects
    if len([field for field in g.camel_track[g.BOARD_SIZE:] if len(field) > 0]) > 0:
        # Make sure to not score the end of the round twice if the end of the game happens to be
        # a natural end of a round
        if not end_of_round_scored:
            end_of_round(g)
        end_of_game(g)

    return g.CAMELS[camel_index], distance


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
    # Create a temporary dummy track
    dummy_track = copy.deepcopy(g.trap_track)

    # Check if player has places the trap and remove it if so
    remove_old_trap = False
    curr_pos = None
    if g.has_player_placed_trap(player):
        # Remove trap
        # Find old trap position
        [curr_pos] = [[y, row[0]] for y, row in enumerate(g.trap_track) if (row[1] if 0 < len(row) else None) == player]

        # Check that the old position/type and the new position/type aren't identical
        if (curr_pos[0] == trap_place) and (curr_pos[1] == trap_type):
            raise ValueError("Old and new trap position/type are identical")

        remove_old_trap = True
        dummy_track[curr_pos[0]] = []

    # Place trap in new position
    # Check that trap_place and trap_type are legal
    if (trap_place < 1) or (trap_place > g.BOARD_SIZE):
        raise ValueError("Illegal value for trap_place")
    if trap_type not in (1, -1):
        raise ValueError("Illegal value for trap_type")

    # Check that spot isn't occupied by a camel
    if len(g.camel_track[trap_place]) != 0:
        raise ValueError("trap_place occupied by camel")

    # Check that spot isn't occupied by or next to an existing trap
    if (len(dummy_track[trap_place - 1]) != 0) or \
       (len(dummy_track[trap_place]) != 0) or \
       (len(dummy_track[trap_place + 1]) != 0):
        raise ValueError("trap_place occupied by or next to an existing trap")

    if remove_old_trap:
        g.trap_track[curr_pos[0]] = []
    g.trap_track[trap_place] = [trap_type, player]
    return True


def place_game_bet(g, camel, bet_type, player):
    # Check if the player has already bet on the camel
    if camel in g.get_player_bets(player):
        raise ValueError("Player {} has already bet on camel {}".format(player, camel))

    if bet_type == "win":
        g.game_winner_bets.append([camel, player])
    elif bet_type == "lose":
        g.game_loser_bets.append([camel, player])
    else:
        raise ValueError("Invalid bet type")


def place_round_winner_bet(g, camel, player):
    if (__ROUND_BET_ACTION_ID, camel) not in get_valid_moves(g, player):
        raise ValueError("Player {} attempted to make an invalid round bet on camel {}".format(player, camel))
    g.round_bets.append([camel, player])
    return True


def end_of_round(g):
    first_place_payout_index = 0
    second_place_payout_index = 0

    first_place_camel = find_camel_in_nth_place(g, 1)
    second_place_camel = find_camel_in_nth_place(g, 2)

    # Payout
    for bet in g.round_bets:
        if bet[0] == first_place_camel:
            payout = g.FIRST_PLACE_ROUND_PAYOUT[first_place_payout_index]
            g.player_money_values[bet[1]] += payout
            first_place_payout_index += 1
            print_update(
                msg="Paid player #{} {} coins for selecting the round winner".format(bet[1], payout),
                display_updates=g.verbose)
        elif bet[0] == second_place_camel:
            payout = g.SECOND_PLACE_ROUND_PAYOUT[second_place_payout_index]
            g.player_money_values[bet[1]] += payout
            second_place_payout_index += 1
            print_update(
                msg="Paid player #{} {} coins for selecting the round runner up".format(bet[1], payout),
                display_updates=g.verbose)
        else:
            payout = g.THIRD_OR_WORSE_PLACE_ROUND_PAYOUT
            g.player_money_values[bet[1]] += payout
            print_update(
                msg="Paid player #{} {} coins for selecting the third or worse camel".format(bet[1], payout),
                display_updates=g.verbose)

    # Prepare GameState for the beginning of next round
    g.camel_yet_to_move = [True, True, True, True, True]
    g.round_bets = []  # clear round bets

    # Uncomment this if traps should be reset to their players after each round
    # g.trap_track = [[] for i in range(finish_line)]
    return


def end_of_game(g):
    winning_camel = find_camel_in_nth_place(g, 1)  # Find camel that won
    losing_camel = find_camel_in_nth_place(g, g.NUM_CAMELS)  # Find camel that lost

    # Settle bets on winning camel
    payout_index = 0
    for bet in g.game_winner_bets:
        if bet[0] == winning_camel:
            payout = g.get_game_bets_payout(payout_index)
            g.player_money_values[bet[1]] += payout
            print_update(
                msg="Paid Player #{} {} coins for betting on the game winner".format(bet[1], payout),
                display_updates=g.verbose)
            payout_index += 1
        else:
            print_update(
                msg="Paid Player #{} {} coins for incorrectly betting on the game winner".format(
                    bet[1], g.BAD_GAME_END_BET),
                display_updates=g.verbose)
            g.player_money_values[bet[1]] += g.BAD_GAME_END_BET

    # Settle bets on losing camel
    payout_index = 0
    for bet in g.game_loser_bets:
        if bet[0] == losing_camel:
            payout = g.get_game_bets_payout(payout_index)
            g.player_money_values[bet[1]] += payout
            print_update(
                msg="Paid Player #{} {} coins for betting on the game loser".format(bet[1], payout),
                display_updates=g.verbose)
            payout_index += 1
        else:
            print_update(
                msg="Paid Player #{} {} coins for incorrectly betting on the game loser".format(
                    bet[1], g.BAD_GAME_END_BET),
                display_updates=g.verbose)
            g.player_money_values[bet[1]] += g.BAD_GAME_END_BET

    g.active_game = False
    g.game_winner = [i for i, j in enumerate(g.player_money_values) if j == max(g.player_money_values)]
    return True


def find_camel_in_nth_place(g, n):
    track = g.camel_track
    if n > g.NUM_CAMELS or n < 1:
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


def display_game_state(g):
    if g.verbose:
        print("Track:")
        display_track_state(g.camel_track)
        print("\n")
        print("Traps:")
        display_track_state(g.trap_track)
        print("\n")
        print("$ Totals:")
        print("\t" + str(g.player_money_values))
        print("\n")


def display_track_state(g):
    track = g.camel_track
    if not g.verbose:
        return None

    max_stack = len(max(track, key=len))

    # Print milestones
    track_label_string = "\t|"
    for _ in range(0, g.BOARD_SIZE):
        track_label_string += ("-" + str(_) + "-|")
    print(track_label_string)

    # Print blank line
    track_label_string = "\t"
    for i in range(0, g.BOARD_SIZE):
        track_label_string += ("---" + "-" * len(str(i)))
    print(track_label_string + "-")

    # Print N/A if there are no objects (camels/traps)
    if max_stack == 0:
        track_label_string = "\t  "  # extra spaces because double digit numbers mess things up
        for _ in range(0, g.BOARD_SIZE):
            track_label_string += "  "
        print(track_label_string + "NA")

    # otherwise print those objects
    for stack_spot in range(0, max_stack):
        track_string = "\t"
        for track_spot in range(0, g.BOARD_SIZE):
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
    for i in range(0, g.BOARD_SIZE):
        track_label_string += ("---" + "-" * len(str(i)))
    print(track_label_string + "-")
    # Print milestones again

    track_label_string = "\t|"
    for _ in range(0, g.BOARD_SIZE):
        track_label_string += ("-" + str(_) + "-|")
    print(track_label_string)
