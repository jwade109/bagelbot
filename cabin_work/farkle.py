#! /usr/bin/env python3

import random
import itertools
import collections
import sys
from copy import copy
import statistics
import time
from functools import lru_cache as cache

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
def score(subset, level=0):
    if not subset:
        return 0, ""

    subset = list(subset)

    if subset == [5]:
        return 50, "one 5"
    if subset == [1]:
        return 100, "one 1"
    if subset == [5, 5]:
        return 100, "two 5s"
    if subset == [1, 1]:
        return 200, "two 1s"
    if len(subset) == 1:
        return 0, "one 1"
    if subset == [1, 1, 1]:
        return 300, "three 1s"
    if subset == [3, 3, 3]:
        return 300, "three 3s"
    if subset == [2, 2, 2]:
        return 200, "three 2s"
    if subset == [4, 4, 4]:
        return 400, "three 4s"
    if subset == [5, 5, 5]:
        return 500, "three 5s"
    if subset == [6, 6, 6]:
        return 600, "three 6s"
    if len(unique(tuple(subset))) == 1: # N if a kind
        if len(subset) == 4:
            return 1000, f"four {subset[0]}s"
        if len(subset) == 5:
            return 2000, f"five {subset[0]}s"
        if len(subset) == 6:
            return 3000, f"six {subset[0]}s"
    if is_straight(tuple(subset)):
        return 1500, "straight"
    if len(subset) == 6:
        c = collections.Counter(subset)
        counts = list(c.values())
        if counts == [3, 3]:
            return 2500, "two triplets"
        if counts == [2, 2, 2] or counts == [4, 2] or counts == [2, 4]:
            return 1500, "three pairs"

    for comb in all_combinations(tuple(subset)):
        if subset == list(comb):
            continue
        comb = list(comb)
        d = dual(tuple(subset), tuple(comb))
        s1, h1 = score(tuple(comb), level + 1)
        s2, h2 = score(tuple(d), level + 1)
        if s1 > 0 and s2 > 0:
            hint = h1 + ", " + h2
            if not h1:
                hint = h2
            if not h2:
                hint = h1
            return s1 + s2, h1 + ", " + h2
    return 0, ""

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
        s, h = score(tuple(c))
        if s:
            opts.append((c, s, h))
    return opts

def liststr(iterable):
    return " ".join([f"[{x}]" for x in iterable])

def turn(strategy, total_score, r):
    turn_score = 0
    num_rolls = 1
    while r:
        opts = sorted(get_options(tuple(r)), key=lambda x: x[1])
        if not opts:
            return 0, num_rolls

        choice, should_reroll = strategy(r, opts, turn_score, total_score)

        next = opts[choice]
        keep = next[0]
        turn_score += next[1]
        reroll = len(dual(tuple(r), tuple(keep)))
        if not reroll:
            reroll = 6
        if not should_reroll:
            return turn_score, num_rolls
        r = d6(reroll)
        num_rolls += 1

    return turn_score, num_rolls

STRATS_TO_EVAL = []
def strategy(functor):
    STRATS_TO_EVAL.append(functor)
    return functor

@strategy
def greedy(r, opts, turn_score, ts):
    return len(opts) - 1, turn_score < 1000

@strategy
def naive(r, opts, turn_score, ts):
    c = len(opts) - 1
    opt = opts[c]
    can_reroll = len(dual(tuple(r), tuple(opt[0])))
    return c, can_reroll > 2

@strategy
def minmax(r, opts, turn_score, total_score):
    c = 0
    opt = opts[c]
    can_reroll = len(dual(tuple(r), tuple(opt[0])))
    return c, can_reroll > 2

@strategy
def treebeard(r, opts, turn_score, total_score):
    c = 0
    for i, (dice, score, hint) in enumerate(opts):
        if turn_score + score == 350:
            turn_score += score
            c = i
    should_reroll = turn_score < 350
    return c, should_reroll

@strategy
def stop_after_350(r, opts, turn_score, total_score):
    c = len(opts) - 1
    opt = opts[c]
    turn_score += opt[1]
    return c, turn_score < 350 

@strategy
def conservative(r, opts, turn_score, total_score):
    c = len(opts) - 1
    roll, s, h = opts[c]
    can_reroll = len(dual(tuple(r), tuple(roll)))
    return len(opts) - 1, False

def interactive(r, opts, turn_score, total_score):
    print(f"Score: {total_score} ({turn_score} points this turn)")
    print("\n   " + liststr(r) + "\n")
    for i, (dice, s, hint) in enumerate(opts):
        reroll = len(dual(tuple(r), tuple(dice)))
        hint_str = f" ({hint})" if hint else ""
        print(f"({i+1}) {s} pts\t{liststr(dice):24s} ({reroll} remaining)")
    print()
    print("Which option? ", end="")
    index = int(input()) - 1
    opt = opts[index]
    can_reroll = len(dual(tuple(r), tuple(opt[0])))
    if not can_reroll:
        can_reroll = 6
    turn_score += opt[1]
    print(f"You've earned {turn_score} points this turn.")
    print(f"Reroll {can_reroll} dice? (default is yes) ", end="")
    should_reroll = 'n' not in input()
    return index, should_reroll

def evaluate(strategies, n=1000):
    scores = {}
    for strat in strategies:
        scores[strat.__name__] = [[], []]
    for i in range(n):
        r = d6(6)
        for strat in strategies:
            s, nr = turn(strat, 0, r)
            scores[strat.__name__][0].append(s)
            scores[strat.__name__][1].append(nr)
    return scores

def eval_main():
    evaluation = evaluate(STRATS_TO_EVAL, 10000)
    for strat, (scores, turns) in evaluation.items():
        print(f"{strat:17s}{statistics.mean(scores):10.2f}" \
            f"{statistics.mean(turns):10.2f}" \
            f"{max(scores):10.2f}" \
            f"{statistics.stdev(scores):10.2f}" \
            f"{sum([1 if x == 0 else 0 for x in scores]):8}")

def main():
    computer_score = 0
    user_score = 0
    turn_counter = 0
    
    while computer_score < 10000 and user_score < 10000:
        turn_counter += 1
        print(f"\n====== TURN {turn_counter} ======\n")
        print("====== BEGIN COMPUTER TURN ======")
        turn_score, rolls = turn(naive, computer_score, d6(6))
        computer_score += turn_score
        print(f"Computer has {computer_score} points.\n")
        print("======= END COMPUTER TURN =======\n")

        time.sleep(1)

        print("====== BEGIN PLAYER TURN ======")
        turn_score, rolls = turn(interactive, user_score, d6(6))
        user_score += turn_score
        print(f"Player has {user_score} points.\n")
        print("======= END PLAYER TURN =======")

        print("Press enter to continue...")
        input()

    print(f"\n\nGAME END AFTER {turn_counter} TURNS")
    print(f"Computer: {computer_score}")
    print(f"Treebeard: {user_score}")

if __name__ == "__main__":
    main()

