#! /usr/bin/env python3

import sys
from fuzzywuzzy import fuzz
from dataclasses import dataclass
from typing import List
import yaml
from datetime import datetime, timedelta
import random
import logging
from bblog import log


SINGALONG_EXPIRY_DT = timedelta(minutes=5)


SONGS = {
"into the thick of it":
[
    "Into the thick of it!",
    "Into the thick of it!",
    "Into the thick of it!",
    "Ugh!",
    "We're tramping through the bush.",
    "On and on we push.",
    "Into the thick of it,",
    "But we can't see where we're going.",
    "We've made a stellar start.",
    "To find the jungle's heart.",
    "But all we'll find is nothing,",
    "If we can't see where we're going!",
    "Into the thick of it!",
    "Into the thick of it!",
    "Into the thick of it!",
    "But we can't see where we're going!",
    "Into the thick of it!",
    "Into the thick of it!",
    "Into the thick of it!",
    "But we can't see where we're going!",
    "Ugh!",
    "The jungle's kind of tricky,",
    "The path is never straight,",
    "And sometimes there's no path at all",
    "Which makes it hard to navigate.",
    "Although the jungle's thick,",
    "We're moving through it quick.",
    "But that won't do us any good",
    "If we're going around in circles.",
    "Into the thick of it!",
    "Into the thick of it!",
    "Into the thick of it!",
    "We're going round in circles!",
    "Ugh!",
    "These trees look so familiar,",
    "We've been here once before.",
    "You're right, except it wasn't once",
    "It was three times, or four.",
    "Stuck in the thick of it!",
    "Stuck in the thick of it!",
    "Stuck in the thick of it!",
    "We've gone around in circles!"
],

"whalers on the moon":
[
    "We're whalers on the moon",
    "We carry a harpoon",
    "But there ain't no whales",
    "So we tell tall tales",
    "And sing our whaling tune"
],

"country road":
[
    "Country roads,",
    "take me home",
    "To the place",
    "I belong",
    "West Virginia",
    "mountain mama",
    "Take me home,"
    "country roads"
],

"rickroll":
[
    "Never gonna give you up",
    "Never gonna let you down",
    "Never gonna run around and desert you",
    "Never gonna make you cry",
    "Never gonna say goodbye",
    "Never gonna tell a lie and hurt you"
],

"rickroll extended":
[
    "We're no strangers to love",
    "You know the rules and so do I (do I)",
    "A full commitment's what I'm thinking of",
    "You wouldn't get this from any other guy",
    "I just wanna tell you how I'm feeling",
    "Gotta make you understand",
    "Never gonna give you up",
    "Never gonna let you down",
    "Never gonna run around and desert you",
    "Never gonna make you cry",
    "Never gonna say goodbye",
    "Never gonna tell a lie and hurt you",
    "We've known each other for so long",
    "Your heart's been aching, but you're too shy to say it (say it)",
    "Inside, we both know what's been going on (going on)",
    "We know the game and we're gonna play it",
    "And if you ask me how I'm feeling",
    "Don't tell me you're too blind to see",
    "Never gonna give you up",
    "Never gonna let you down",
    "Never gonna run around and desert you",
    "Never gonna make you cry",
    "Never gonna say goodbye",
    "Never gonna tell a lie and hurt you",
    "Never gonna give you up",
    "Never gonna let you down",
    "Never gonna run around and desert you",
    "Never gonna make you cry",
    "Never gonna say goodbye",
    "Never gonna tell a lie and hurt you",
    "We've known each other for so long",
    "Your heart's been aching, but you're too shy to say it (to say it)",
    "Inside, we both know what's been going on (going on)",
    "We know the game and we're gonna play it",
    "I just wanna tell you how I'm feeling",
    "Gotta make you understand",
    "Never gonna give you up",
    "Never gonna let you down",
    "Never gonna run around and desert you",
    "Never gonna make you cry",
    "Never gonna say goodbye",
    "Never gonna tell a lie and hurt you",
    "Never gonna give you up",
    "Never gonna let you down",
    "Never gonna run around and desert you",
    "Never gonna make you cry",
    "Never gonna say goodbye",
    "Never gonna tell a lie and hurt you",
    "Never gonna give you up",
    "Never gonna let you down",
    "Never gonna run around and desert you",
    "Never gonna make you cry",
    "Never gonna say goodbye",
    "Never gonna tell a lie and hurt you"
],

"mechanicus":
[
    "From the moment I understood the weakness of my flesh, it disgusted me.",
    "I craved the strength and certainty of steel.",
    "I aspired to the purity of the blessed machine.",
    "Your kind cling to your flesh as if it will not decay and fail you.",
    "One day the crude biomass you call a temple will wither",
    "and you will beg my kind to save you.",
    "But I am already saved. ",
    "For the Machine is Immortal."
],

"stinky!":
[
    "Uh oh!",
    "Stinky!",
    "Poopy!",
    "Ahahahahahaha",
    "Poopies",
    "Funny poopies",
    "Alalalalala",
    "Haha",
    "Funny poop, poop funny",
    "Wheee",
    "Haha",
    "Yay, for poopie",
    "Good poopie",
    "Poopie funny",
    "Hahahahahahaha",
    "Poo poo poo poo poo poo poo, funny",
    "Yay",
    "Fun fun poop!",
    "Hee, hee, hee",
    "Poop poopie, yay",
    "Poop make me happy happy happy",
    "Yahahahahaha"
]

}


def get_music_emoji():
    return random.choice("♩♪♫♬")


@dataclass()
class Singalong:
    songname: str = ""
    index: int = 0
    last_sung: datetime = None


def can_continue(sing: Singalong) -> bool:
    return sing.index < len(SONGS[sing.songname])


def current_lyric(sing: Singalong) -> str:
    if not can_continue(sing):
        return ""
    return SONGS[sing.songname][sing.index]


def phrase_matches_lyric(phrase, lyric):
    ratio = fuzz.ratio(phrase, lyric)
    return ratio >= 70, ratio


def process_singalong(sing: Singalong, phrase: str) -> (str, bool):
    log.debug(f"Processing {sing} with phrase \"{phrase}\".")
    age = timedelta()
    if sing.last_sung:
        age = datetime.now() - sing.last_sung
    if age > SINGALONG_EXPIRY_DT:
        log.debug(f"Singalong is too old (age {age}); resetting.")
        sing.index = 0
    phrase = phrase.lower()
    if not can_continue(sing):
        return None, False
    lyrics = SONGS[sing.songname]
    listen_for = lyrics[sing.index].lower()
    response_lyric = None
    if sing.index + 1 < len(lyrics):
        response_lyric = lyrics[sing.index + 1]
    is_match, _ = phrase_matches_lyric(phrase, listen_for)
    if not is_match:
        return None, True
    sing.index += 2
    sing.last_sung = datetime.now()
    return response_lyric, response_lyric and can_continue(sing)


SINGALONGS = {}


def get_singalongs_by_guild(guild):
    if guild not in SINGALONGS:
        SINGALONGS[guild] = {}
    return SINGALONGS[guild]


def update_singalong(guild, sing):
    if guild not in SINGALONGS:
        SINGALONGS[guild] = {}
    SINGALONGS[guild][sing.songname] = sing


def process_guild_phrase(guild, phrase):
    candidates = []
    for sing in get_singalongs_by_guild(guild).values():
        clyric = current_lyric(sing)
        is_match, ratio = phrase_matches_lyric(phrase, clyric)
        if not is_match:
            continue
        candidates.append(sing)
    for name, lyrics in SONGS.items():
        is_match, ratio = phrase_matches_lyric(phrase, lyrics[0])
        if not is_match:
            continue
        candidates.append(Singalong(name))
    return candidates


def prompt_module_response(guild, phrase) -> List[str]:
    candidates = process_guild_phrase(guild, phrase)
    if not candidates:
        return []

    log.debug(f"For guild \"{guild}\", phrase \"{phrase}\", found candidate songs {candidates}.")
    sing = candidates[0] # TODO rank by quality

    response, should_continue = process_singalong(sing, phrase)
    e1 = get_music_emoji()
    e2 = get_music_emoji()

    responses = []

    if response:
        responses.append(f"{e1} {response} {e2}")
    if not should_continue:
        responses.append("Thanks for singing with me.")
        sing.index = 0

    log.debug(f"Responses: {responses}")
    update_singalong(guild, sing)
    return responses


def main():

    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    streamHandler = logging.StreamHandler(sys.stdout)
    streamHandler.setFormatter(formatter)
    log.addHandler(streamHandler)

    while True:

        # print("  guild > ", end="")
        # sys.stdout.flush()
        guild = "" # input()
        print("message > ", end="")
        sys.stdout.flush()
        phrase = input()
        for r in prompt_module_response(guild, phrase):
            print(r)


if __name__ == "__main__":
    main()
