#! /usr/bin/env python3

import random
import itertools
import collections
import sys
from copy import copy
import statistics
import time
from functools import lru_cache as cache
import logging
from dataclasses import dataclass, field
import asyncio
from emoji import emojize
from bagelshop.logging import log

from state_machine import set_param, get_param

DICE = [
"""\
*--------*
|        |
|   ██   |
|        |
*--------*\
""",
"""\
*--------*
| ██     |
|        |
|     ██ |
*--------*\
""",
"""\
*--------*
|     ██ |
|   ██   |
| ██     |
*--------*\
""",
"""\
*--------*
| ██  ██ |
|        |
| ██  ██ |
*--------*\
""",
"""\
*--------*
| ██  ██ |
|   ██   |
| ██  ██ |
*--------*\
""",
"""\
*--------*
| ██  ██ |
| ██  ██ |
| ██  ██ |
*--------*\
"""
]

def draw_dice(list_of_dice):
    concat = []
    n_lines = len(DICE[0].split("\n"))
    dice_strs = [DICE[n-1].split("\n") for n in list_of_dice]
    ret = ""
    for i, lines in enumerate(zip(*dice_strs)):
        ret += "  ".join(lines)
        if i + 1 < n_lines:
            ret += "\n"
    return ret

@dataclass(frozen=True)
class Option:
    score: int = None
    dice: tuple = None

@dataclass(frozen=True)
class RollData:
    roll: tuple = None
    options: list = None
    banked: tuple = None
    rerolled: int = None
    score: int = None

@dataclass()
class Turn:
    rolls: list = None
    score: int = None
    strategy: str = None

@cache(None)
def unique(stuff):
    t = type(stuff)
    return t(set(stuff))

@cache(None)
def all_combinations(rolls):
    ret = []
    for L in range(1, len(rolls) + 1):
        for subset in itertools.combinations(rolls, L):
            subset = tuple(sorted(subset))
            ret.append(subset)
    ret = list(set(ret))
    ret = sorted(ret, key=lambda x: (len(x), x))
    return ret

@cache(None)
def dual(all, subset):
    ret = list(copy(all))
    for x in subset:
        ret.remove(x)
    return ret

@cache(None)
def score(subset):
    if not subset:
        return 0

    subset = list(subset)

    if subset == [5]:
        return 50
    if subset == [1]:
        return 100
    if subset == [5, 5]:
        return 100
    if subset == [1, 1]:
        return 200
    if len(subset) == 1:
        return 0
    if subset == [1, 1, 1]:
        return 300
    if subset == [3, 3, 3]:
        return 300
    if subset == [2, 2, 2]:
        return 200
    if subset == [4, 4, 4]:
        return 400
    if subset == [5, 5, 5]:
        return 500
    if subset == [6, 6, 6]:
        return 600
    if len(unique(tuple(subset))) == 1: # N if a kind
        if len(subset) == 4:
            return 1000
        if len(subset) == 5:
            return 2000
        if len(subset) == 6:
            return 3000
    if is_straight(tuple(subset)):
        return 1500
    if len(subset) == 6:
        c = collections.Counter(subset)
        counts = list(c.values())
        if counts == [3, 3]:
            return 2500
        if counts == [2, 2, 2] or counts == [4, 2] or counts == [2, 4]:
            return 1500

    for comb in all_combinations(tuple(subset)):
        if subset == list(comb):
            continue
        comb = list(comb)
        d = dual(tuple(subset), tuple(comb))
        s1 = score(tuple(comb))
        s2 = score(tuple(d))
        if s1 > 0 and s2 > 0:
            return s1 + s2
    return 0

def d6(num=1):
    return sorted([random.randint(1, 6) for x in range(num)])

@cache(None)
def is_straight(rolls):
    return len(rolls) == 6 and \
        1 in rolls and \
        2 in rolls and \
        3 in rolls and \
        4 in rolls and \
        5 in rolls and \
        6 in rolls

@cache(None)
def get_options(roll):
    opts = []
    for c in all_combinations(roll):
        s = score(tuple(c))
        if s:
            opt = Option(s, c)
            opts.append(opt)
    return opts

def liststr(iterable):
    return " ".join([f"[{x}]" for x in iterable])

def dicestr(iterable):
    return " ".join("{}\N{COMBINING ENCLOSING KEYCAP}".format(i) for i in iterable)

async def turn(strategy, r):
    ret = Turn([], 0, strategy.__name__)
    log.debug(f"roll={r}, strat={strategy.__name__}")
    while r:
        opts = sorted(get_options(tuple(r)), key=lambda x: x.score)
        log.debug(f"opts: {opts}")
        if not opts:
            log.debug(f"Strategy {strategy.__name__} farkled!")
            ret.rolls.append(RollData(r, opts, (), 0, 0))
            ret.score = 0
            return ret

        choice, should_reroll = await strategy(r, opts, ret.score)
        log.debug(f"Opted for choice={choice}, should_reroll={should_reroll}")

        chosen = opts[choice]
        reroll = len(dual(tuple(r), tuple(chosen.dice)))
        if not reroll:
            reroll = 6
        ret.rolls.append(RollData(r, opts, chosen.dice, reroll, chosen.score))
        ret.score += chosen.score
        if not should_reroll:
            return ret
        r = d6(reroll)

    return ret

def turn_info_to_str(turn_info):
    ret = f"TI >> Rolls: {len(turn_info.rolls)}; " \
        f"Strategy: {turn_info.strategy}; "
    ret += f"Score: {turn_info.score}\n" if turn_info.score else "Farkle!\n"
    for i, r in enumerate(turn_info.rolls):
        ret += f"Roll {i+1}: {list(r.roll)}, banked {list(r.banked)} for {r.score} pts"
        if i + 1 < len(turn_info.rolls):
            ret += "\n"
    return ret

def score_turn(turn_info):
    return turn_info.score, len(turn_info.rolls)

STRATS_TO_EVAL = []
def strategy(functor):
    STRATS_TO_EVAL.append(functor)
    return functor

@strategy
async def greedy(r, opts, turn_score):
    c = len(opts) - 1
    new_score = turn_score + opts[c].score
    return len(opts) - 1, new_score < 1000

@strategy
async def naive(r, opts, turn_score):
    c = len(opts) - 1
    opt = opts[c]
    can_reroll = len(dual(tuple(r), opt.dice))
    return c, can_reroll > 2 or can_reroll == 0

@strategy
async def minmax(r, opts, turn_score):
    c = 0
    opt = opts[c]
    can_reroll = len(dual(tuple(r), opt.dice))
    return c, can_reroll > 2

@strategy
async def stop_after_350(r, opts, turn_score):
    c = len(opts) - 1
    opt = opts[c]
    turn_score += opt.score
    return c, turn_score < 350

@strategy
async def conservative(r, opts, turn_score):
    c = len(opts) - 1
    option = opts[c]
    can_reroll = len(dual(tuple(r), tuple(option.dice)))
    return len(opts) - 1, False

async def interactive(r, opts, turn_score):
    print("\n   " + liststr(r) + "\n")
    for i, option in enumerate(opts):
        reroll = len(dual(tuple(r), tuple(option.dice)))
        print(f"({i+1}) {option.score} pts\t{liststr(option.dice):24s} ({reroll} remaining)")
    print()
    print("Which option? ", end="")
    index = int(input()) - 1
    opt = opts[index]
    can_reroll = len(dual(tuple(r), tuple(opt.dice)))
    if not can_reroll:
        can_reroll = 6
    turn_score += opt.score
    print(f"You've earned {turn_score} points this turn.")
    print(f"Reroll {can_reroll} dice? (default is yes) ", end="")
    should_reroll = 'n' not in input()
    return index, should_reroll

def evaluate(strategies, n=1000):
    loop = asyncio.get_event_loop()
    scores = {}
    for strat in strategies:
        scores[strat.__name__] = [[], []]
    for i in range(n):
        r = d6(6)
        for strat in strategies:
            s, nr = score_turn(loop.run_until_complete(turn(strat, r)))
            scores[strat.__name__][0].append(s)
            scores[strat.__name__][1].append(nr)
    return scores

def leaderboard_to_string():
    farkle = get_param("farkle_database", {})
    k = list(farkle.keys())
    for user in k:
        if "bagelbot" in user:
            del farkle[user]
    df = pandas.DataFrame.from_dict(farkle, orient="index")
    df.sort_values("avg score", inplace=True, ascending=False)
    st = df.to_string(float_format=lambda x: f"{x:0.2f}",
        header=["Average Score", "Farkles", "Top Score", "Turns"])
    return st

def evaluate_stragies(N=500):
    eval_strats = STRATS_TO_EVAL
    evaluation = evaluate(eval_strats, N)
    print(f"Evaluate {len(eval_strats)} strategies, N={N}")
    print(f"{'Strategy':17s}{'Avg Score':>12s}{'Avg Turns':>12s}" \
        f"{'Max Score':>12s}{'STDEV':>12s}{'Farkle Rate':>14s}")
    for strat, (scores, turns) in evaluation.items():
        print(f"{strat:17s}{statistics.mean(scores):12.2f}" \
            f"{statistics.mean(turns):12.2f}" \
            f"{max(scores):12.2f}" \
            f"{statistics.stdev(scores):12.2f}" \
            f"{sum([1 if x == 0 else 0 for x in scores])/len(scores):14.3f}")

def cli_game():
    computer_score = 0
    user_score = 0
    turn_counter = 0

    loop = asyncio.get_event_loop()

    while computer_score < 10000 and user_score < 10000:
        turn_counter += 1
        print(f"\n====== TURN {turn_counter} ======\n")
        print("====== BEGIN COMPUTER TURN ======")
        turn_score, rolls = score_turn(loop.run_until_complete(turn(naive, d6(6))))
        computer_score += turn_score
        print(f"Computer has {computer_score} points.\n")
        print("======= END COMPUTER TURN =======\n")

        time.sleep(1)

        print("====== BEGIN PLAYER TURN ======")
        turn_score, rolls = score_turn(loop.run_until_complete(turn(interactive, d6(6))))
        user_score += turn_score
        print(f"Player has {user_score} points.\n")
        print("======= END PLAYER TURN =======")

        print("Press enter to continue...")
        input()

    print(f"\n\nGAME END AFTER {turn_counter} TURNS")
    print(f"Computer: {computer_score}")
    print(f"Player: {user_score}")

def register_score(username, score):
    log.info(f"{username} scored {score} points.")
    farkle = get_param("farkle_database", {})
    if username not in farkle:
        farkle[username] = {"turns": 0, "top score": None, "avg score": None, "farkles": 0}

    udb = farkle[username]
    avg = udb["avg score"]
    top = udb["top score"] if udb["top score"] else 0

    alpha = 0.85
    udb["top score"] = max(top, score)
    udb["avg score"] = score if avg is None else alpha * avg + (1 - alpha) * score
    udb["turns"] += 1
    if not score:
        udb["farkles"] += 1
    farkle[username] = udb
    set_param("farkle_database", farkle)


if __name__ == "__main__":
    evaluate_stragies()
    exit()

import discord
from discord.ext import commands


class FarkleMessage:

    def __init__(self, ctx):
        self.ctx = ctx
        self.handle = None
        self.committed_text = ""
        self.staged_text = ""
        self.warned_about_permissions = False

    async def add_text(self, new_text, defer_send=False):
        am = discord.AllowedMentions(users=False)
        self.staged_text += new_text
        if not self.handle:
            to_send = self.committed_text = self.staged_text
            self.handle = await self.ctx.send(to_send, allowed_mentions=am)
            self.committed_text = to_send
            self.staged_text = ""
        elif not defer_send:
            try:
                to_send = self.committed_text + self.staged_text
                await self.handle.edit(content=to_send, allowed_mentions=am)
                self.committed_text = to_send
                self.staged_text = ""
            except discord.errors.HTTPException:
                to_send = self.staged_text
                self.handle = await self.ctx.send(content=to_send, allowed_mentions=am)
                self.committed_text = to_send
                self.staged_text = ""

    async def clear_emojis(self):
        if not self.handle:
            return
        try:
            await self.handle.clear_reactions()
        except:
            if not self.warned_about_permissions:
                await self.ctx.send("Uh oh. For this game to be fully functional, " \
                    "I need the \"Manage Messages\" permission on this server. " \
                    "(I only use this permission to modify emojis in Farkle games.)")
            self.warned_about_permissions = True


class Farkle(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def farkle(self, ctx):
        if isinstance(ctx.channel, discord.channel.DMChannel):
            await ctx.send("Sorry, you can't play Farkle in a DM with " \
                "me due to limitations in Discord's API. Yes, I know it's stupid.")
            return

        roll = d6(6)

        def number_to_letter(i):
            return chr(65 + i)

        def number_emoji(i):
            return chr(int(f"0001F1{format(230 + i, 'x').upper()}", 16))

        fark = FarkleMessage(ctx)
        await fark.add_text(f"🎲 🎲 {ctx.message.author.mention} is playing Farkle! 🎲 🎲")

        async def discord_interactive(r, opts, turn_score):
            await fark.add_text(f"\n\nYou rolled **{dicestr(r)}**.\n```", True)
            for i, opt in enumerate(opts):
                await fark.add_text(f"\n[{number_to_letter(i)}]: " \
                    f"Keep {liststr(opt.dice)} for {opt.score} points", True)
            await fark.add_text("\n```Please select your dice from the options above.")
            option_emojis = [number_emoji(i) for i in range(len(opts))]
            for oe in option_emojis:
                await fark.handle.add_reaction(oe)

            c = len(opts) - 1 # choose best option by default
            should_reroll = False # don't reroll by default

            def check_option(reaction, user):
                return reaction.message == fark.handle and user == ctx.message.author and \
                    str(reaction.emoji) in option_emojis

            try:
                reaction, user = await self.bot.wait_for("reaction_add", check=check_option, timeout=120)
            except asyncio.TimeoutError:
                log.debug("Waiting for Farkle option selection timed out.")
                await fark.add_text(f"\nTimed out.")
                await fark.clear_emojis()
                return c, should_reroll

            c = option_emojis.index(str(reaction.emoji))
            log.info(f"{ctx.message.author} selected option {c}.")
            await fark.add_text(f"\nSelected option {number_emoji(c)}.")
            await fark.clear_emojis()
            new_score = turn_score + opts[c].score
            dice_to_reroll = len(dual(tuple(r), tuple(opts[c].dice)))
            if not dice_to_reroll:
                dice_to_reroll = 6
            await fark.add_text(f"\n\nWould you like to reroll **{dice_to_reroll} dice** (🎲), " \
                f"or bank **{new_score} points** (💰)?\n")

            await fark.handle.add_reaction("🎲")
            await fark.handle.add_reaction("💰")

            def check_reroll(reaction, user):
                return reaction.message == fark.handle and user == ctx.message.author and \
                    str(reaction.emoji) in ["🎲", "💰"]

            try:
                reaction, user = await self.bot.wait_for("reaction_add", check=check_reroll, timeout=120)
            except asyncio.TimeoutError:
                log.debug("Waiting for Farkle reroll selection timed out.")
                await fark.add_text(f"\nTimed out.")
                await fark.clear_emojis()
                return c, should_reroll

            should_reroll = str(reaction.emoji) == "🎲"
            await fark.clear_emojis()
            if should_reroll:
                await fark.add_text(f"🎲 Take risks, Farkle!")
            else:
                await fark.add_text(f"💰 Ending this turn with {new_score} points.")
            return c, should_reroll

        turn_info = await turn(discord_interactive, roll)

        turn_info.strategy = str(ctx.message.author)
        register_score(str(ctx.message.author), turn_info.score)
        if not turn_info.score:
            last_roll = turn_info.rolls[-1]

            await fark.add_text(f"\n\nSorry, you farkled! (roll was {dicestr(last_roll.roll)})")
        else:
            await fark.add_text(f"\n\nCongrats, you got {turn_info.score} points!")


    @commands.command(name="farkle-eval")
    async def farkle_eval(self, ctx, *opt_dice_rolls):
        if opt_dice_rolls and len(opt_dice_rolls) > 6:
            await ctx.send("Sorry, standard Farkle rules permit only up to 6 dice.")
            return
        if opt_dice_rolls:
            try:
                r = [int(x) for x in opt_dice_rolls]
            except:
                await ctx.send("Sorry, I had trouble parking ")
            log.info(f"Hey, {ctx.message.author} is farkling. They provided {r}.")
            to_send = f"Here's how various Farkle strategies performed " \
                "with the initial die rolls you provided:\n"
        else:
            r = d6(6)
            log.info(f"Hey, {ctx.message.author} is farkling. They rolled {r}.")
            to_send = f"You rolled {r}. Here's how various strategies performed:\n"
        to_send += "```\n" + draw_dice(r) + "```\n"
        for strategy in STRATS_TO_EVAL:
            ti = await turn(strategy, r)
            score, _ = score_turn(ti)
            register_score("bagelbot/" + strategy.__name__, score)
            text = turn_info_to_str(ti)
            to_send += "```\n" + text + "\n```\n"
        await ctx.send(to_send)

    # @commands.command(name="farkle-leaderboard", aliases=["fklb"])
    # async def lb(self, ctx):
    #     text = leaderboard_to_string()
    #     await ctx.send("```\n" + text + "```")

