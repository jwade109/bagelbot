#! /usr/bin/env python3

import sys
import os
from functools import lru_cache, partial
import random
import time
import re
from dataclasses import dataclass, field
from random import randint
from yaml import YAMLObject
from copy import copy
from state_machine import set_param, get_param
from ws_dir import WORKSPACE_DIRECTORY

YAML_PATH = WORKSPACE_DIRECTORY + "/private/othello.yaml"

# FYI: black always goes first

NUMBER_OF_DIRS = 8 # coincidence
EMPTY = 0 # ":black_medium_small_square:"
BLACK = 1 # ":red_circle:"
WHITE = 2 # ":blue_circle:"


@dataclass()
class GameState(YAMLObject):
    yaml_tag = u'!GameState'
    uid: int = field(default_factory=lambda: randint(0, 1E12))
    w: int = 0
    h: int = 0
    moves: list = field(default_factory=list)
    finished: bool = False
    stalemate: bool = False
    black_user_uid: int = 0
    white_user_uid: int = 0


def make_empty_board(w, h):
    return [[EMPTY]*h for i in range(w)]


def make_starting_board(w, h):
    board = make_empty_board(w, h)
    cx, cy = w // 2 - 1, h // 2 - 1
    board[cx  ][cy  ] = BLACK
    board[cx  ][cy+1] = WHITE
    board[cx+1][cy  ] = WHITE
    board[cx+1][cy+1] = BLACK
    return board


def get_board_dims(board):
    h = len(board[0])
    w = len(board)
    return w, h


def other_color(color):
    if color == BLACK:
        return WHITE
    if color == WHITE:
        return BLACK
    return EMPTY


def is_valid_coord(x, y, w, h):
    return x >= 0 and x < w and y >= 0 and y < h


def iter_coords_in_dir(x, y, d, w, h):
    dxs = [0, 1, 1, 1, 0, -1, -1, -1]
    dys = [1, 1, 0, -1, -1, -1, 0, 1]
    dx, dy = dxs[d], dys[d]
    i, j = x, y
    while True:
        i += dx
        j += dy
        if is_valid_coord(i, j, w, h):
            yield i, j
        else:
            break


def iter_board_coords(w, h):
    for i in range(w):
        for j in range(h):
            yield i, j


def is_straight_capture_condition(tiles, color):
    if not tiles:
        return False
    if tiles[0] != other_color(color):
        return False
    for i in range(1, len(tiles)):
        if tiles[i] == color:
            return True
        if tiles[i] == EMPTY:
            return False
    return False


def get_all_moves(board, color):
    for i, j in iter_board_coords(*get_board_dims(board)):
        if is_capture_move(color, board, i, j):
            yield i, j


def is_capture_move(color, board, x, y):
    if board[x][y] != EMPTY:
        return False
    for d in range(NUMBER_OF_DIRS):
        tiles = list(get_tiles_in_dir(board, x, y, d))
        if is_straight_capture_condition(tiles, color):
            return True
    return False


def get_tiles_in_dir(board, x, y, d):
    w, h = get_board_dims(board)
    for i, j in iter_coords_in_dir(x, y, d, w, h):
        yield board[i][j]


def commit_move(board, x, y, color):
    board[x][y] = color
    w, h = get_board_dims(board)
    for d in range(NUMBER_OF_DIRS):
        tiles = list(get_tiles_in_dir(board, x, y, d))
        if not is_straight_capture_condition(tiles, color):
            continue
        for i, j in iter_coords_in_dir(x, y, d, w, h):
            if board[i][j] != other_color(color):
                break
            board[i][j] = color


def eval_board(board):
    white, black = 0, 0
    w, h = get_board_dims(board)
    for i, j in iter_board_coords(w, h):
        val = board[i][j]
        if val == WHITE:
            white += 1
        if val == BLACK:
            black += 1
    completed = white + black == w * h
    return white, black, completed


def transpose(board):
    w, h = get_board_dims(board)
    ret = make_empty_board(h, w)
    for i, j in iter_board_coords(*get_board_dims(board)):
        ret[j][i] = board[i][j]
    return ret


def line_notation(board):
    flattened = []
    for i, j in iter_board_coords(*get_board_dims(board)):
        flattened.append(board[j][i])
    curr = None
    count = 0
    counts = []
    for v in flattened:
        if v != curr:
            if count > 0:
                counts.append((count, curr))
                count = 0
            curr = v
        count += 1
    return ",".join("{}{}".format(*c) for c in counts)


def render_board(board):

    DEFAULT_EMPTY_STR = "  " # "  "
    DEFAULT_BLACK_STR = "<>" # "░░"
    DEFAULT_WHITE_STR = "[]" # "██"

    def cell_to_str(num):
        if num == BLACK:
            return DEFAULT_BLACK_STR
        if num == WHITE:
            return DEFAULT_WHITE_STR
        return DEFAULT_EMPTY_STR

    w, h = get_board_dims(board)
    to_print = transpose(board)
    ret = "\n     " + "-" * (w * 2) + "\n"
    for i, row in enumerate(reversed(to_print)):
       ret += f" {(h - i) % 10} | " + "".join(cell_to_str(r) for r in row) + " |\n"
    ret += "     " + "-" * (w * 2) + "\n"
    ret += "     " + " ".join(chr(x + 65) for x in range(w)) + "\n\n"
    return ret


def get_current_turn_color(list_of_moves):
    return BLACK if len(list_of_moves) % 2 == 0 else WHITE


def render_game(game: GameState):
    return f"Game ID: {game.uid}\n" \
        f"Turn Number: {len(game.moves)}\n" \
        f"Moves: {','.join(str(x) for x in game.moves)}\n" \
        f"Current Turn: {get_current_turn_color(game.moves)}\n" \
        f"Finished: {game.finished}\n" \
        f"Stalemate: {game.stalemate}\n" \
        f"Black User: {game.black_user_uid}\n" \
        f"White User: {game.white_user_uid}\n" \
        f"{render_board(board_from_movelist(game.moves, game.w, game.h))}\n"


def print_board(board):
    print(render_board(board))


def print_game(game):
    print(render_game(game))


def has_reached_stalemate(list_of_moves):
    return len(list_of_moves) > 1 and \
        not list_of_moves[-1] and not list_of_moves[-2]


def board_from_movelist(moves, w, h):
    board = make_starting_board(w, h)
    color = BLACK # starts with black!
    for move in moves:
        if move:
            commit_move(board, *move, color)
        color = other_color(color)
    return board


def make_new_game(w, h):
    game = GameState()
    game.w, game.h = w, h
    return game


def step_game(game, move_strategy):
    board = board_from_movelist(game.moves, game.w, game.h)
    current_turn = get_current_turn_color(game.moves)
    moves = list(get_all_moves(board, current_turn))
    if moves:
        x, y = move_strategy(board, current_turn, moves)
        commit_move(board, x, y, current_turn)
        game.moves.append([x, y])
    else:
        game.moves.append([])
    ws, bs, game.finished = eval_board(board)
    if has_reached_stalemate(game.moves):
        game.finished = True
        game.stalemate = True


def simulate_game(move_strategy, w, h):
    game = GameState()
    game.w = w
    game.h = h
    board = make_starting_board(w, h)
    ws, bs, game.finished = eval_board(board)
    while not game.finished:
        step_game(game, move_strategy)
    return game


def random_strategy(board, color, moves):
    return random.choice(moves)


def human_readable_coords(x, y):
    return f"{chr(x + 65)}{y+1}"


def alphabetical_to_dec(text: str) -> int:
    t = text.upper()
    def value(i, c):
        v = pow(26, i) * (ord(c) - 65)
        return v
    ret = sum(value(*c) for c in enumerate(reversed(t)))
    return ret


def parse_readable_coords(readable: str) -> (int, int):
    pattern = r"([a-zA-Z]+)(\d+)"
    matches = re.search(pattern, readable)
    if not matches:
        return None
    x = alphabetical_to_dec(matches.group(1))
    y = int(matches.group(2)) - 1
    return x, y


def ask_strategy(board, color, moves):
    print_board(board)
    human_readable = ", ".join(human_readable_coords(x, y) \
        for x, y in moves)
    print(f"Turn: {color}, moves: {human_readable}")
    print("Please select a move: ", end="")
    sys.stdout.flush()
    while True:
        text = input()
        coords = parse_readable_coords(text)
        if coords:
            if coords in moves:
                return coords
            else:
                print(f"\"{text}\" is not a valid move: ", end="")
        else:
            print("Please provide a valid move index: ", end="")
        sys.stdout.flush()


def is_user_in_game(game, user_agent):
    return user_agent in [game.black_user_uid, game.white_user_uid]


def add_or_update_game(games_db, game):
    games_db[game.uid] = game


def write_games_to_disk(games):
    set_param("othello_games", games, YAML_PATH)

def read_games_from_disk():
    return get_param("othello_games", {}, YAML_PATH)


def main():

    game = make_new_game(4, 4)
    while not game.finished:
        print_game(game)
        step_game(game, random_strategy)
    print_game(game)
    set_param("othello_games", {game.uid: game}, YAML_PATH)


if __name__ == "__main__":
    main()


import discord
from discord.ext import commands, tasks


class Othello(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.games = read_games_from_disk()

    @commands.command()
    async def othello(self, ctx, *args):
        game = simulate_game(random_strategy, 4, 4)
        await ctx.send("```\n" + render_game(game) + "\n```")

    @commands.command(name="othello-challenge")
    async def othello_challenge(self, ctx, another_user: discord.User):

        self_id = ctx.message.author.id
        other_id = another_user.id

        for game in self.games.values():
            if is_user_in_game(game, self_id) and is_user_in_game(game, other_id):
                await ctx.send("You're already in a game with " \
                    f"{another_user}:\n```\n{render_game(game)}\n```")
                return

        if another_user.id == self.bot.user.id:
            await ctx.send(f"Oh, you're approaching me? I'll make a new game for us.")
        else:
            await ctx.send(f"Ok, creating a new game between you and {another_user}.")

        game = make_new_game(8, 8)
        game.black_user_uid = self_id
        game.white_user_uid = other_id
        await ctx.send("```\n" + render_game(game) + "\n```")
        add_or_update_game(self.games, game)
        write_games_to_disk(self.games)
