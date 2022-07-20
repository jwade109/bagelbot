#! /usr/bin/env python3

import sys
import os
from functools import lru_cache, partial
import random
import time
import re
from dataclasses import dataclass, field
from random import randint
import yaml
from yaml import YAMLObject
from copy import copy


# FYI: black always goes first

NUMBER_OF_DIRS = 8 # coincidence
EMPTY = "E" # ":black_medium_small_square:"
BLACK = "B" # ":red_circle:"
WHITE = "W" # ":blue_circle:"
TRUE  = "T" # "+"

EMPTY_MOVE = "-"

DEFAULT_EMPTY_STR = "  "
DEFAULT_BLACK_STR = "░░"
DEFAULT_WHITE_STR = "██"


@dataclass()
class GameState(YAMLObject):
    yaml_tag = u'!GameState'
    uid: int = field(default_factory=lambda: randint(0, 1E12))
    w: int = 0
    h: int = 0
    moves: list = field(default_factory=list)
    current_turn: str = BLACK
    finished: bool = False
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


def evaluate_over_board(board, predicate):
    ret = make_empty_board()
    for i, j in iter_board_coords():
        ret[i][j] = TRUE if predicate(board, i, j) else EMPTY
    return ret


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
        f"Moves: {','.join(game.moves)}\n" \
        f"Current Turn: {get_current_turn_color(game.moves)}\n" \
        f"Finished: {game.finished}\n" \
        f"Black User: {game.black_user_uid}\n" \
        f"White User: {game.white_user_uid}\n" \
        f"{render_board(board_from_movelist(game.moves, game.w, game.h))}\n"


def print_board(board):
    print(render_board(board))


def print_game(game):
    print(render_game(game))


def has_reached_stalemate(list_of_moves):
    return len(list_of_moves) > 1 and \
        list_of_moves[-1] == EMPTY_MOVE and \
        list_of_moves[-2] == EMPTY_MOVE


def board_from_movelist(moves, w, h):
    board = make_starting_board(w, h)
    color = BLACK # starts with black!
    for move in moves:
        if move == EMPTY_MOVE:
            continue
        x, y = [int(i) for i in move.split("-")] # TODO: bad
        commit_move(board, x, y, color)
        color = other_color(color)
    return board


def simulate_game(move_strategy, w, h):

    game = GameState()
    game.w = w
    game.h = h
    game.current_turn = BLACK
    board = make_starting_board(w, h)
    ws, bs, game.finished = eval_board(board)

    while not game.finished:

        # print_game(game)
        # time.sleep(0.05)

        moves = list(get_all_moves(board, game.current_turn))
        if moves:
            x, y = move_strategy(board, game.current_turn, moves)
            commit_move(board, x, y, game.current_turn)
            game.moves.append(f"{x}-{y}")
        else:
            game.moves.append(EMPTY_MOVE)
        game.current_turn = other_color(game.current_turn)
        ws, bs, game.finished = eval_board(board)

        if has_reached_stalemate(game.moves):
            game.finished = True

    # print(f"Done. White: {ws}; Black: {bs}")
    # print_board(board)
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


def main():

    while True:
        game = simulate_game(random_strategy, 8, 8)

        print_game(game)
        time.sleep(0.02)

        print(yaml.dump(game))


if __name__ == "__main__":
    main()


import discord
from discord.ext import commands, tasks


class Othello(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def othello(self, ctx, *args):
        game = simulate_game(random_strategy, 8, 8)
        await ctx.send("```\n" + render_game(game) + "\n```")
