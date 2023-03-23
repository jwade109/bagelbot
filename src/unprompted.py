import discord
from discord.ext import commands
from datetime import datetime, timedelta
from thickofit import prompt_module_response as singalong
import logging
import random
import validators
import resource_paths as rps
import requests
from bs4 import BeautifulSoup # for bacon
from pathlib import Path


log = logging.getLogger("unprompted")
log.setLevel(logging.DEBUG)


def sanitize_spooky_chrs(string):
    return string.replace("’", "'")


def clean_message(msg_text):
    return sanitize_spooky_chrs(msg_text).strip().lower()


# duplicate of bot.py! deduplicate later
# get a bunch of text from this very silly web API
def get_wisdom():
    html = requests.get(f"https://fungenerators.com/random/sentence").content
    soup = BeautifulSoup(html, 'html.parser')
    ret = soup.find("h2").get_text()
    if len(ret) > 1800:
        ret = ret[:1800]
    return ret


MESSAGE_HOOKS = []
def message_hook(priority, throttle_rate=1):
    def ret(functor):
        MESSAGE_HOOKS.append((functor, priority, throttle_rate))
        return functor
    return ret


@message_hook(10)
def singalong_hook(msg):
    cleaned = clean_message(msg.content)
    song_responses = singalong(str(msg.guild), cleaned)
    return song_responses


@message_hook(5)
def hot_damn_hook(msg):
    cleaned = clean_message(msg.content)
    if "too hot" in cleaned:
        return ["*𝅗𝅥 Hot damn 𝅘𝅥*"]
    return []


ROCK_AND_STONE = [
    "Rock and stone!",
    "Rock and stone foreveh!",
    "We fight for rock and stone!",
    "Come on guys, rock and stone!",
    "Did I hear a rock and stone!?",
    "That's it lads, rock and stone!",
    "Rock and stone, brotha!",
    "Yeah! Rock and stone!",
    "If you don't rock and stone, you ain't comin home.",
    "For rock and stone!",
    "Rock and stone, yeah!",
    "Rock and stone everyone!",
    "Rock and stone to the bone!",
    "Rock and stone in the heart!",
    "Rock and roll and stone!",
    "By the beard!",
    "Rock solid!",
    "For Karl!"
]


@message_hook(5)
def rock_and_stone_hook(msg):
    cleaned = clean_message(msg.content)
    if "rock" in cleaned and "stone" in cleaned:
        return [random.choice(ROCK_AND_STONE)]
    if "were rich" in cleaned or "we're rich" in cleaned:
        return ["We're rich!"]
    return []


@message_hook(4, 0.03)
def bplacement_hook(msg):
    words = clean_message(msg.content).split()
    words = [w for w in words if len(w) > 10]
    if not words:
        return []

    selection = random.choice(words)
    if selection.startswith("<@"): # discord user mention
        return []
    elif validators.url(selection):
        return []

    if selection[0] in ['a', 'e', 'i', 'o', 'u', 'l', 'r']:
        make_b = "B" + selection
    else:
        make_b = "B" + selection[1:]
    if make_b[-1] != ".":
        make_b = make_b + "."
    return [make_b]


@message_hook(1, 0.01)
def stupid_fish_hook(msg):
    return [Path(random.choice([rps.DUMB_FISH_PATH, rps.MONKEY_PATH]))]


@message_hook(1, 0.01)
def wisdom_hook(msg):
    w = get_wisdom()
    return [w] if w else []


@message_hook(3, 0.1)
def joe_mama_hook(msg):
    cleaned = clean_message(msg.content)
    if "joe" in cleaned:
        return ["Joe mama!"]
    return []


class Unprompted(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author == self.bot.user:
            return

        has_fired = False
        for hook, priority, rate in sorted(MESSAGE_HOOKS, key=lambda x: -x[1]):
            res = hook(message)
            rand = random.random()
            lt_gt = '<' if rand < rate else '>'
            should_fire = rand < rate and res
            # log.debug(f"{hook.__name__} ({priority}): {res} ({100*rand:0.2f}% {lt_gt}" \
            #     f" {100*rate}%) [{'YES' if should_fire else 'NO'}]")
            if not should_fire:
                continue
            if res and not has_fired:
                for r in res:
                    log.info(f"For message \"{message.content}\" in {message.channel.guild}...")
                    log.info(f"Sending: {r}")
                    if isinstance(r, Path):
                        await message.channel.send(file=discord.File(str(r)))
                    else:
                        await message.channel.send(str(r))
                has_fired = True

