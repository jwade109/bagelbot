#! /usr/bin/env python3

import sys

from fuzzywuzzy import fuzz
from dataclasses import dataclass
from typing import List


@dataclass()
class Singalong:
    lyrics: List[str]
    index: int = 0


LYRICS = """Into the thick of it!
Into the thick of it!
Ugh!
We're tramping through the bush.
On and on we push.
Into the thick of it,
But we can't see where we're going.
We've made a stellar start.
To find the jungle's heart.""".split("\n")
# But all we'll find is nothing,
# If we can't see where we're going!
# Into the thick of it!
# Into the thick of it!
# Into the thick of it!
# But we can't see where we're going!
# Into the thick of it!
# Into the thick of it!
# Into the thick of it!
# But we can't see where we're going!
# Ugh!
# The jungle's kind of tricky,
# The path is never straight,
# And sometimes there's no path at all
# Which makes it hard to navigate.
# Although the jungle's thick,
# We're moving through it quick.
# But that won't do us any good
# If we're going around in circles.
# Into the thick of it!
# Into the thick of it!
# Into the thick of it!
# We're going round in circles!
# Ugh!
# These trees look so familiar,
# We've been here once before.
# You're right, except it wasn't once
# It was three times, or four.
# Stuck in the thick of it!
# Stuck in the thick of it!
# Stuck in the thick of it!
# We've gone around in circles!""".split("\n")


print(f"{len(LYRICS)} loaded.")


def can_continue(sing: Singalong) -> bool:
    return sing.index < len(sing.lyrics)


def process_singalong(sing: Singalong, phrase: str) -> (str, bool):
    phrase = phrase.lower()
    if not can_continue(sing):
        return None, False
    listen_for = sing.lyrics[sing.index].lower()
    response_lyric = None
    if sing.index + 1 < len(sing.lyrics):
        response_lyric = sing.lyrics[sing.index + 1]
    ratio = fuzz.ratio(phrase, listen_for)
    if ratio < 70:
        return None, True
    sing.index += 2
    return response_lyric, response_lyric and can_continue(sing)


def main():
    sing = Singalong(LYRICS)
    should_continue = True

    while True:

        print("> ", end="")
        sys.stdout.flush()
        phrase = input()

        response, should_continue = process_singalong(sing, phrase)
        if response:
            print(response)
        if not should_continue:
            print("Thanks for singing with me.")
            sing.index = 0


if __name__ == "__main__":
    main()
