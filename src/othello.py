#! /usr/bin/env python3

import sys
import os
from typing import List
from functools import lru_cache, partial
import random
import time
import re
import asyncio
import random
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from random import randint
from yaml import YAMLObject
import yaml
import logging
from state_machine import set_param, get_param
from ws_dir import WORKSPACE_DIRECTORY

log = logging.getLogger("othello")
log.setLevel(logging.DEBUG)

YAML_PATH = WORKSPACE_DIRECTORY + "/private/othello.yaml"

# FYI: blue always goes first

NUMBER_OF_DIRS = 8 # coincidence


class Color(Enum):
    EMPTY = 0
    BLUE = 1
    RED = 2


@dataclass()
class Player(YAMLObject):
    yaml_tag = u'!Player'
    uid: int = 0
    uname: str = ""


@dataclass()
class GameState(YAMLObject):
    yaml_tag = u'!GameState'
    uid: int = field(default_factory=lambda: randint(0, 1E12))
    w: int = 0
    h: int = 0
    moves: list = field(default_factory=list)
    blue: Player = field(default_factory=Player)
    red: Player = field(default_factory=Player)


@dataclass()
class GameMetaData():
    game_over: bool = False
    stalemate: bool = False
    winner: Player = None
    loser: Player = None
    winning_score: int = 0
    losing_score: int = 0
    blue_score: int = 0
    red_score: int = 0
    current_turn_color: Color = Color.EMPTY
    current_turn_user: Player = field(default_factory=Player)
    next_turn_color: Color = Color.EMPTY
    next_turn_user: Player = field(default_factory=Player)
    available_moves: List = field(default_factory=list)
    board: List = field(default_factory=list)


def make_empty_board(w, h):
    return [[Color.EMPTY]*h for i in range(w)]


def make_starting_board(w, h):
    board = make_empty_board(w, h)
    cx, cy = w // 2 - 1, h // 2 - 1
    board[cx  ][cy  ] = Color.BLUE
    board[cx  ][cy+1] = Color.RED
    board[cx+1][cy  ] = Color.RED
    board[cx+1][cy+1] = Color.BLUE
    return board


def get_board_dims(board):
    h = len(board[0])
    w = len(board)
    return w, h


def other_color(color: Color):
    if color == Color.BLUE:
        return Color.RED
    if color == Color.RED:
        return Color.BLUE
    return Color.EMPTY


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
        if tiles[i] == Color.EMPTY:
            return False
    return False


def get_all_moves(board, color):
    for i, j in iter_board_coords(*get_board_dims(board)):
        if is_capture_move(color, board, i, j):
            yield i, j


def get_all_game_moves(game: GameState):
    board = board_from_movelist(game.moves, game.w, game.h)
    color = get_current_turn_color(game.moves)
    return get_all_moves(board, color)


def is_capture_move(color, board, x, y):
    if board[x][y] != Color.EMPTY:
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


def commit_game_move(game, move):
    current_turn = get_current_turn_color(game.moves)
    log.debug(f"For game {game.uid}, turn " \
        f"{turn_to_str(current_turn)}, committing move {move}")
    game.moves.append(move)


def eval_game_metadata(game: GameState) -> GameMetaData:
    md = GameMetaData()
    md.board = board_from_movelist(game.moves, game.w, game.h)
    md.available_moves = list(get_all_game_moves(game))
    for i, j in iter_board_coords(game.w, game.h):
        val = md.board[i][j]
        if val == Color.RED:
            md.red_score += 1
        if val == Color.BLUE:
            md.blue_score += 1
    md.stalemate = has_reached_stalemate(game.moves)
    filled = (md.red_score + md.blue_score) == game.w * game.h
    md.game_over = filled or md.stalemate
    md.current_turn_color = get_current_turn_color(game.moves)
    md.next_turn_color = other_color(md.current_turn_color)

    if md.current_turn_color == Color.BLUE:
        md.current_turn_user = game.blue
        md.next_turn_user = game.red
    elif md.current_turn_color == Color.RED:
        md.current_turn_user = game.red
        md.next_turn_user = game.blue

    md.winning_score = max(md.blue_score, md.red_score)
    md.losing_score = min(md.blue_score, md.red_score)

    if md.red_score >= md.blue_score:
        md.winner = game.red
        md.loser = game.blue
    else:
        md.winner = game.blue
        md.loser = game.red

    return md


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


def board_to_emojis(board):

    blue  = ":blue_circle:"
    red   = ":red_circle:"
    blank = ":black_medium_small_square:"

    def cell_to_str(num):
        if num == Color.BLUE:
            return blue
        if num == Color.RED:
            return red
        return blank

    w, h = get_board_dims(board)
    to_print = transpose(board)
    ret = ""
    SINGLE_DIGIT_NUMBERS_AS_TEXT = ["one", "two", "three", "four", "five",
        "six", "seven", "eight", "nine", "ten"]
    for i, row in enumerate(reversed(to_print)):
        ri = h - i - 1
        digit = SINGLE_DIGIT_NUMBERS_AS_TEXT[ri % 10]
        ret += f":{digit}: "
        ret += " ".join(cell_to_str(r) for r in row) + "\n"
    ret += blank
    for i in range(w):
        c = chr(ord('a') + (i % 26))
        ret += f" :regional_indicator_{c}:"
    return ret


def get_current_turn_color(list_of_moves):
    return Color.BLUE if len(list_of_moves) % 2 == 0 else Color.RED


def turn_to_str(turn):
    if turn == Color.RED:
        return "Red"
    if turn == Color.BLUE:
        return "Blue"
    return "???"


def turn_to_color(turn):
    if turn == Color.RED:
        return 0xff2b2b
    if turn == Color.BLUE:
        return 0x6666ff
    return 0


def has_reached_stalemate(list_of_moves):
    return len(list_of_moves) > 1 and \
        not list_of_moves[-1] and not list_of_moves[-2]


def board_from_movelist(moves, w, h):
    board = make_starting_board(w, h)
    color = Color.BLUE # starts with blue!
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
    moves = list(get_all_game_moves(game))
    choice = []
    if moves:
        x, y = move_strategy(board, current_turn, moves)
        commit_move(board, x, y, current_turn)
        choice = [x, y]
    commit_game_move(game, choice)


def step_game_until_moves_available_or_game_over(game):
    md = eval_game_metadata(game)
    while not md.available_moves and not md.game_over:
        log.debug(f"Adding an empty move, since none are available for {md.current_turn_user}")
        game.moves.append([])
        md = eval_game_metadata(game)


def simulate_game(move_strategy, w, h):
    game = GameState()
    game.w = w
    game.h = h
    md = eval_game_metadata(game)
    while not md.game_over:
        step_game(game, move_strategy)
        md = eval_game_metadata(game)
    return game


def random_strategy(board, color, moves):
    return random.choice(moves)


def human_readable_coords(move):
    if not move:
        return "[x]"
    x, y = move
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
    human_readable = ", ".join(human_readable_coords(m) \
        for m in moves)
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
    return user_agent in [game.blue.uid, game.red.uid]


def add_or_update_game(games_db, game):
    games_db[game.uid] = game


def is_it_agent_turn(game, user_agent):
    if not is_user_in_game(game, user_agent):
        return False
    color = get_current_turn_color(game.moves)
    user_color = Color.BLUE if user_agent == game.blue.uid else Color.RED
    return color == user_color


def write_games_to_disk(games):
    set_param("othello_games", games, YAML_PATH)


def read_games_from_disk():
    return get_param("othello_games", {}, YAML_PATH)


def write_user_plays_to_disk(plays):
    set_param("othello_user_plays", plays, YAML_PATH)


def read_user_plays_from_disk():
    return get_param("othello_user_plays", {}, YAML_PATH)


def main():
    game = make_new_game(8, 8)
    print_game(game)
    step_game(game, random_strategy)
    print_game(game)


if __name__ == "__main__":
    main()


import discord
from discord.ext import commands, tasks


async def fetch_user_noexcept(client, uid):
    log.debug(f"Fetching user with UID {uid}")
    try:
        u = await client.fetch_user(uid)
        log.debug(f"For UID {uid}, got user {u}")
        return u
    except Exception as e:
        log.error(f"Failed to get user {uid}: {e}")
    return None


async def fetch_users_from_game(client, game: GameState):
    return await fetch_user_noexcept(client, game.blue.uid), \
           await fetch_user_noexcept(client, game.red.uid)


def game_to_embed(game, debug=False):
    log.debug(f"Converting this game to embed: {game}")
    md = eval_game_metadata(game)

    turn = get_current_turn_color(game.moves)
    if turn == Color.BLUE:
        current_user = game.blue
        last_user = game.red
    else:
        current_user = game.red
        last_user = game.blue

    last_move = None
    if game.moves:
        last_move = game.moves[-1]

    summary = ""
    if md.game_over:
        stlmt_str = " (A stalemate has been reached.)" if md.stalemate else ""
        summary = f"Game over!{stlmt_str}\n\n"
        if md.winning_score != md.losing_score:
            summary += f"<@{md.winner.uid}>, with {md.winning_score} points, " \
                f"has beaten <@{md.loser.uid}>, with {md.losing_score}."
        else:
            summary += f"<@{game.blue.uid}> and <@{game.red.uid}> have tied, " \
                f"each with {md.winning_score}."
    else:
        if last_move:
            summary += f"<@{md.next_turn_user.uid}> just played {human_readable_coords(last_move)}.\n\n"
        elif last_move is not None:
            summary += f"<@{md.next_turn_user.uid}> didn't have any legal moves available.\n\n"
        summary += f"It's now <@{md.current_turn_user.uid}>'s turn."

    available_moves = "No available moves"
    if md.available_moves:
        available_moves = ", ".join(human_readable_coords(m) for m in md.available_moves)

    embed_color = turn_to_color(md.current_turn_color)
    if md.game_over:
        embed_color = 0x00a143
    embed = discord.Embed(title=f"{game.blue.uname} (Blue) vs {game.red.uname} (Red)",
        description=f"{summary}\n\n{board_to_emojis(md.board)}\n", color=embed_color)
    if not md.game_over:
        embed.add_field(name="Available Moves", value=available_moves, inline=False)
    if debug:
        embed.add_field(name="Debug", value=f"{game}", inline=False)
    return embed


def games_to_embed(games: List[GameState], agent_display_name):
    desc = ""
    for g in games:
        desc += f"{g}\n\n"
    embed = discord.Embed(title=f"{agent_display_name}'s Othello Games",
        description=desc)
    return embed


DONT_ALERT_USERS = discord.AllowedMentions(users=False)


class Othello(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.games = read_games_from_disk()
        self.user_plays = read_user_plays_from_disk()

    def last_game_id(self, user_agent):
        if user_agent not in self.user_plays:
            return None
        return self.user_plays[user_agent]

    def set_last_game_id(self, user_agent, game_uid):
        self.user_plays[user_agent] = game_uid
        write_user_plays_to_disk(self.user_plays)

    @commands.command(name="othello-show", aliases=["ok"])
    async def othello_show(self, ctx, game_uid: int):
        log.debug(f"Got UID {game_uid}.")
        if not game_uid in self.games:
            await ctx.send(f"UID {game_uid} doesn't appear to be associated with any game.")
            return
        game = self.games[game_uid]
        embed = game_to_embed(game, True)
        await ctx.send("Found this game.", embed=embed)

    @commands.command(name="othello-delete", aliases=["od"])
    async def othello_delete(self, ctx, game_uid: int):
        log.debug(f"Got UID {game_uid}.")
        if not game_uid in self.games:
            await ctx.send(f"UID {game_uid} doesn't appear to be associated with any game.")
            return
        game = self.games[game_uid]
        embed = game_to_embed(game)
        del self.games[game_uid]
        write_games_to_disk(self.games)
        await ctx.send("Deleted this game.", embed=embed)

    async def process_bot_play(self, ctx, game):
        md = eval_game_metadata(game)
        if md.current_turn_user.uid != self.bot.user.id:
            return
        if md.game_over:
            await ctx.send("It appears the game is over; I have no strong feelings one way or the other.")
            return

        log.info(f"It's my turn to play in game {game.uid}!")
        await ctx.send("Thinking about my next move in my game with " \
            f"<@{md.next_turn_user.uid}>...", allowed_mentions=DONT_ALERT_USERS)
        # make it look like bagelbot is thinking
        await asyncio.sleep(random.randint(2, 7))
        # pick a random ass move
        step_game(game, random_strategy)
        step_game_until_moves_available_or_game_over(game)
        add_or_update_game(self.games, game)
        write_games_to_disk(self.games)
        embed = game_to_embed(game)
        await ctx.send("I've just made a move.", embed=embed)

    @commands.command(name="othello-play", aliases=["o"])
    async def othello_play(self, ctx, movestr, another_user: discord.User = None):
        agent_id = ctx.message.author.id
        log.debug(f"Agent {agent_id} ({ctx.message.author}): " \
            f"{movestr} (disambiguated by user {another_user})")

        move = parse_readable_coords(movestr)
        if not move:
            await ctx.send(f"Failed to parse that move: {movestr}")
            return 1
        log.debug(f"Parsed move coordinates {move}.")

        last_game_id = self.last_game_id(agent_id)
        log.debug(f"Last play was {last_game_id}.")

        game = None
        if another_user:
            other_id = another_user.id
            pred = lambda g: is_user_in_game(g, agent_id) and is_user_in_game(g, other_id)
            games = list(filter(pred, self.games.values()))
            if not games:
                await ctx.send(f"There are no games between you and {another_user}.")
                return
            if len(games) > 1:
                await ctx.send(f"More than one game was found between you and {another_user}.")
                return
            log.debug("User disambiguation returned a game.")
            game = games[0]
        elif last_game_id and last_game_id in self.games:
            log.debug("Using the previous game, since no disambiguation provided.")
            game = self.games[last_game_id]
        else:
            pred = lambda g: is_user_in_game(g, agent_id)
            games = list(filter(pred, self.games.values()))
            if not games:
                await ctx.send("You're not currently in any games. To start a game, " \
                    "use othello-challenge, and @ the person you want to challenge.")
                return
            if len(games) > 1:
                log.debug("Game choice is ambiguous.")
                await ctx.send("Uh oh, you're currently in multiple Othello games, " \
                    "and I'm not sure which one you want to play in. " \
                    "Please disambiguate (only once is required) by @ing the " \
                    "person you're playing after your move.")
                return
            log.debug("User is only in one game, so the choice is unambiguous.")
            game = games[0]
        log.debug(f"Using this game: {game}")
        self.set_last_game_id(agent_id, game.uid)

        md = eval_game_metadata(game)
        if md.current_turn_user.uid != agent_id:
            await ctx.send(f"For game <@{game.blue.uid}> vs. <@{game.red.uid}>, " \
                "It's not your turn. Please wait for " \
                f"<@{md.current_turn_user.uid}> to play.",
                allowed_mentions=DONT_ALERT_USERS)
            await self.process_bot_play(ctx, game)
            return

        log.debug(f"Available moves for {turn_to_str(md.current_turn_color)}: {md.available_moves}")
        if move not in md.available_moves:
            vmstr = ", ".join(human_readable_coords(m) for m in md.available_moves)
            log.debug("Invalid move.")
            await ctx.send(f"For game <@{game.blue.uid}> vs. <@{game.red.uid}>, " \
                f"{human_readable_coords(move)} is not a valid move. " \
                f"Valid moves are: {vmstr}", allowed_mentions=DONT_ALERT_USERS)
            return
        log.debug(f"For {turn_to_str(md.current_turn_color)}, commiting move {move}.")
        game.moves.append(list(move))
        step_game_until_moves_available_or_game_over(game)
        add_or_update_game(self.games, game)
        write_games_to_disk(self.games)
        embed = game_to_embed(game)
        await ctx.send(embed=embed)
        await self.process_bot_play(ctx, game)

    @commands.command(name="othello-games", aliases=["og"])
    async def othello_list_games(self, ctx):
        agent_id = ctx.message.author.id
        pred = lambda g: is_user_in_game(g, agent_id)
        games = list(filter(pred, self.games.values()))
        if not games:
            await ctx.send("You're not participating in any games right now.")
            return
        embed = games_to_embed(games, ctx.message.author.display_name)
        await ctx.send("You're currently engaged in these games.", embed=embed)

    @commands.command(name="othello-challenge", aliases=["oc"])
    async def othello_challenge(self, ctx, another_user: discord.Member,
        width: int = 8, height: int = 8):
        """
        Challenge another person (or BagelBot!) to a game of Othello.

        usage:

        bb othello-challenge @kim_mcbudget
        bb othello-challenge @BagelBot

        """

        self_id = ctx.message.author.id
        other_id = another_user.id

        for game in self.games.values():
            if is_user_in_game(game, self_id) and is_user_in_game(game, other_id):
                embed = game_to_embed(game)
                await ctx.send(f"You're already in a game with <@{other_id}>.",
                    embed=embed)
                return

        game = make_new_game(width, height)
        game.blue = Player(self_id, ctx.message.author.display_name)
        game.red = Player(other_id, another_user.display_name)
        add_or_update_game(self.games, game)
        write_games_to_disk(self.games)
        embed = game_to_embed(game)
        self.set_last_game_id(self_id, game.uid)

        if another_user.id == self.bot.user.id:
            await ctx.send(f"Oh, you're approaching me? I'll make a new game for us.",
                embed=embed)
        else:
            await ctx.send(f"Ok, creating a new game between you and <@{other_id}>.",
                embed=embed)
