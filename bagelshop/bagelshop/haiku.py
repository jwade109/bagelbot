#! /usr/bin/env python3

import sys
from nltk.corpus import cmudict
CMU_DICT = cmudict.dict()
# for counting syllables for haiku detection
from curses.ascii import isdigit
import itertools


def most_frequent(elems):
    if not elems:
        return None
    m = 0
    ret = elems[0]
    for e in elems:
        f = elems.count(e)
        if f > m:
            m = f
            ret = e
    return ret


DEBUG_MODE = False

def print_debug(*args, **kwargs):
    if DEBUG_MODE:
        print(*args, **kwargs)


def count_syllables(word):
    low = word.lower()
    for c in ",!?:;.":
        low = low.replace(c, "")
    if low not in CMU_DICT:
        return None
    print_debug(word)
    for s in CMU_DICT[low]:
        print_debug(" ".join(s))
    syl_list = [len(list(y for y in x if isdigit(y[-1]))) for x in CMU_DICT[low]]
    best = most_frequent(syl_list)
    print_debug(word, best)
    return best


def detect_haiku(string):

    string = [x for x in string.split() if x]
    lens = [count_syllables(x) for x in string]
    print_debug(string)
    print_debug(lens)
    if None in lens:
        return None
    cumulative = list(itertools.accumulate(lens))
    print_debug(cumulative)
    if cumulative[-1] != 17 or 5 not in cumulative or 12 not in cumulative:
        return None
    first = " ".join(string[:cumulative.index(5) + 1])
    second = " ".join(string[cumulative.index(5) + 1:cumulative.index(12) + 1])
    third = " ".join(string[cumulative.index(12) + 1:])
    return first, second, third


def main():
    global DEBUG_MODE
    DEBUG_MODE = True
    msg = " ".join(sys.argv[1:])
    if not msg:
        print("Please provide a message to test.")
        return 1
    haiku = detect_haiku(msg)
    if haiku:
        print("Haiku:\n" + "\n".join(haiku))
    else:
        print("Not a haiku.")
    return 0


if __name__ == "__main__":
    exit(main())

