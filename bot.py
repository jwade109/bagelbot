#! /usr/bin/env python3

import os
import sys
import discord
import logging
import re
import random
import asyncio
import traceback
from pathlib import Path
from inspect import signature
import yaml
from animals import Animals
import cowsay
from cowpy import cow
from datetime import datetime
import calendar
import hashlib
import signal
import sys
from PyDictionary import PyDictionary
import wikipedia as wiki
import pypokedex
import editdistance
import wget
import requests
from dataclasses import dataclass
from discord.ext.commands import Bot
from discord.utils import get
from discord import FFmpegPCMAudio
import pyttsx3

import pyttsx3
engine = pyttsx3.init() # object creation
engine.setProperty('rate', 150)

# from stegano import lsb
# from textgenrnn import textgenrnn # future maybe

LOG_FORMAT = "%(levelname)-10s %(asctime)-25s %(name)-22s %(funcName)-18s // %(message)s"
YAML_PATH = "bagelbot_state.yaml"
MEDIA_DOWNLOAD = "media/"
MOZILLA_HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) " \
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
CALVIN_AND_HOBBES_DIR = "ch/"
JUAN_SOTO = "soto.png"
OFFLINE = False
FFMPEG_EXECUTABLE = "C:\\ffmpeg\\bin\\ffmpeg.exe"

bagelbot = Bot(command_prefix=["bagelbot ", "bb ", "$ "])
logging.basicConfig(filename=f"{os.path.dirname(__file__)}/log.txt",
                    level=logging.INFO, format=LOG_FORMAT,
                    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("bagelbot")
log.setLevel(logging.DEBUG)
all_commands = []
startup = datetime.now()
version_hash = hashlib.md5(open(__file__, "r").read().encode("utf-8")).hexdigest()[:8]
dictionary = PyDictionary()

log.info("STARTING. =============================")


def load_yaml():
    if not os.path.exists(YAML_PATH):
        dump_yaml({})
    file = open(YAML_PATH, "r")
    state = yaml.safe_load(file)
    return state


def dump_yaml(dict):
    file = open(YAML_PATH, "w")
    yaml.dump(dict, file, default_flow_style=False)


def set_param(name, value):
    state = load_yaml()
    state[name] = value
    dump_yaml(state)


def get_param(name, default=None):
    state = load_yaml()
    if name in state:
        return state[name]
    print(f"Failed to get parameter {name}, using default: {default}")
    set_param(name, default)
    return default


def download_file(url, destination):
    response = requests.get(url, headers=MOZILLA_HEADERS)
    bin = response.content
    file = open(destination, "wb")
    file.write(bin)
    file.close()


def get_debug_channel(guild):
    for channel in guild.channels:
        if channel.name == "bot-testing":
            return channel
    return None


async def logdebug(string, guild):
    print(f"[{datetime.now()}] [DEBUG] {string}")
    if not OFFLINE:
        channel = get_debug_channel(guild)
        if channel:
            await logchannel(channel, string, True)


async def update_status():
    if OFFLINE:
        return
    bagels = get_param("num_bagels", 0)
    act = discord.Activity(type=discord.ActivityType.watching,
                           name=f" {bagels} bagels")
    await bagelbot.change_presence(activity=act)


@bagelbot.command(help="Get current version of this BagelBot.")
async def version(ctx):
    await ctx.send(f"Firmware MD5 {version_hash}; started at " \
        f"{startup.strftime('%I:%M:%S %p on %B %d, %Y EST')}")


@bagelbot.command(help="Get the definition of a word.")
async def define(ctx, word: str):
    meaning = dictionary.meaning(word)
    if not meaning:
        await ctx.send("Sorry, I couldn't find a definition for '{word}'.")
    ret = f">>> **{word.capitalize()}:**"
    for key, value in meaning.items():
        ret += f"\n ({key})"
        for i, v in enumerate(value):
            ret += f"\n {i+1}. {v}"
    await ctx.send(ret)


@bagelbot.command(help="JUUUAAAAAAANNNNNNNNNNNNNNNNNNNNNNNNNN SOTOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO")
async def soto(ctx):
    await ctx.send(file=discord.File(JUAN_SOTO))


@bagelbot.command(help="Get a picture of an animal and a fun fact about it.")
async def animal(ctx, animal_type: str = ""):
    accepted_types = "cat dog panda koala fox racoon kangaroo".split(" ")
    if animal_type not in accepted_types:
        await ctx.send(f"'{animal_type}' is not a supported animal type; acceptable " \
            f"types are {', '.join(accepted_types)}.")
    animal = Animals(animal_type)
    url = animal.image()
    fact = animal.fact()
    await ctx.send(f"{fact}\n{url}")


@bagelbot.command(help="Perform mathy math on two numbers.")
async def math(ctx, a: int, op: str, b: int):
    if op not in ["+", "-", "*", "/"]:
        await ctx.send("Error: {op} is not a supported math operator.")
    s = a + b + random.randint(-12, 9)
    await ctx.send(f"{a} {op} {b} = {s}. Thanks for playing.")


@bagelbot.command(help="Use a moose to express your thoughts.")
async def moose(ctx, *message):
    cheese = cow.Moose()
    msg = cheese.milk(" ".join(message))
    await ctx.send(f"```\n{msg}\n```")


@bagelbot.command(help="Add two numbers better than previously thought possible.")
async def badmath(ctx, a: int, b: int):
    await ctx.send(f"{a} + {b} = {str(a) + str(b)}. Thanks for playing.")


@bagelbot.command(help="Roll a 20-sided die.")
async def d20(ctx):
    roll = random.randint(1, 20)
    if roll == 20:
        await ctx.send(f"Rolled a 20! :confetti_ball:")
    else:
        await ctx.send(f"Rolled a {roll}.")


@bagelbot.command(help="Download the source code for this bot.")
async def source(ctx):
    url = "https://github.com/jwade109/bagelbot"
    await ctx.send(url, file=discord.File(__file__))


@bagelbot.command(help="Say hi!")
async def hello(ctx):
    await ctx.send(f"Hey, it me, ur bagel.")


@bagelbot.command(name="dean-winchester", help="It's Dean Winchester, from Lost!")
async def dean_winchester(ctx):
    await ctx.send(file=discord.File("dean.gif"))


@bagelbot.command(help="Ask wikipedia for things.")
async def wikipedia(ctx, query: str):
    await ctx.send(wiki.summary(query))


@bagelbot.command(name="bake-bagel", help="Bake a bagel.")
async def bake_bagel(ctx):
    bagels = get_param("num_bagels", 0)
    new_bagels = bagels + 1
    set_param("num_bagels", new_bagels)
    if new_bagels == 1:
        await ctx.send(f"There is now {new_bagels} bagel.")
    if new_bagels == 69:
        await ctx.send(f"There are now {new_bagels} bagels. Nice.")
    await ctx.send(f"There are now {new_bagels} bagels.")
    await update_status()


@bagelbot.command(help="Check how many bagels there are.")
async def bagels(ctx):
    bagels = get_param("num_bagels", 0)
    if bagels == 1:
        await ctx.send(f"There is {bagels} lonely bagel.")
    if bagels == 69:
        await ctx.send(f"There are {bagels} bagels. Nice.")
    await ctx.send(f"There are {bagels} bagels.")
    await update_status()


@bagelbot.command(name="eat-bagel", help="Eat a bagel.")
async def eat_bagel(ctx):
    bagels = get_param("num_bagels", 0)
    if bagels == 0:
        await ctx.send("There are no more bagels!")
    new_bagels = bagels - 1
    set_param("num_bagels", new_bagels)
    if new_bagels == 1:
        await ctx.send(f"There is now {new_bagels} bagel left.")
    if new_bagels == 69:
        await ctx.send(f"There are now {new_bagels} bagels left. Nice.")
    await ctx.send(f"There are now {new_bagels} bagels left.")
    await update_status()


@bagelbot.command(name="good-bot", help="Tell BagelBot it's doing a good job.")
async def good_bot(ctx):
    reports = get_param("kudos", 0)
    set_param("kudos", reports + 1)
    await ctx.send("Thanks.")


@bagelbot.command(name="bad-bot", help="Tell BagelBot it sucks.")
async def bad_bot(ctx):
    reports = get_param("reports", 0)
    set_param("reports", reports + 1)
    await ctx.send("Wanker.")


@bagelbot.command(help="Get info about a pokemon by its name.", category="pokemon")
async def pokedex(ctx, id: int = None):
    if id is None:
        id = random.randint(1, 898)
    if id > 898:
        await ctx.send("There are only 898 pokemon.")
    if id < 1:
        await ctx.send("Only takes numbers greater than zero.")
    try:
        p = pypokedex.get(dex=id)
    except:
        await ctx.send(f"Pokemon `{name}` was not found.")
    await ctx.send(f"{p.name.capitalize()} ({p.dex}). " \
        f"{', '.join([x.capitalize() for x in p.types])} type. " \
        f"{p.weight/10} kg. {p.height/10} m.")
    await ctx.send(f"https://assets.pokemon.com/assets/cms2/img/pokedex/detail/{str(id).zfill(3)}.png")


@bagelbot.command(help="Get info about a pokemon by Pokedex ID.", category="pokemon")
async def pokemon(ctx, name: str = None):
    if not name:
        await pokedex(ctx, None)
        return
    try:
        p = pypokedex.get(name=name)
    except:
        await ctx.send(f"Pokemon `{name}` was not found.")
    await pokedex(ctx, p.dex)


@bagelbot.command(name="rocket-league", help="Make BagelBot play Rocket League.")
async def rocket_league(ctx):
    await ctx.send("PINCH.")


@bagelbot.command(help="Bepis.")
async def bepis(ctx):
    await ctx.send("m" * random.randint(3, 27) + "bepis.")


# @bagelbot.command
def encode(ctx, message: str):
    print(f"Encoding message: {message}")
    """[WIP] Encode a message into an image (stenography)."""
    if not ctx.attachments:
        return "No attachments. Encoding requires an image attachment.", None
    if len(ctx.attachments) > 1:
        return "Too many attachments. Encoding only operates on a single attachment.", None
    if not os.path.exists(MEDIA_DOWNLOAD):
        os.mkdir(MEDIA_DOWNLOAD)
    attach = ctx.attachments[0]
    filename = f"{MEDIA_DOWNLOAD}/encode-{attach.filename}".replace(".jpg", ".png")
    download_file(attach.url, filename)
    # >>> from stegano import lsb
    # >>> secret = lsb.hide("./tests/sample-files/Lenna.png", "Hello World")
    # >>> secret.save("./Lenna-secret.png")
    secret = lsb.hide(filename, message)
    secret.save(filename)
    return ["Done.", Path(filename)], None


# @bagelbot.command
def decode(ctx):
    """[WIP] Decode the message embedded in an image (stenography)."""
    if not ctx.attachments:
        return "No attachments. Encoding requires an image attachment.", None
    if len(ctx.attachments) > 1:
        return "Too many attachments. Encoding only operates on a single attachment.", None
    if not os.path.exists(MEDIA_DOWNLOAD):
        os.mkdir(MEDIA_DOWNLOAD)
    attach = ctx.attachments[0]
    filename = f"{MEDIA_DOWNLOAD}/decode-{attach.filename}".replace(".jpg", ".png")
    download_file(attach.url, filename)
    # >>> clear_message = lsb.reveal("./Lenna-secret.png")
    secret = lsb.reveal(filename)
    return f"Hidden message: ||{secret}||", None


@bagelbot.command(help="Drop some hot Bill Watterson knowledge.")
async def ch(ctx):
    files = [os.path.join(path, filename)
             for path, dirs, files in os.walk(CALVIN_AND_HOBBES_DIR)
             for filename in files
             if filename.endswith(".gif")]
    choice = random.choice(files)
    result = re.search(r".+(\d{4})(\d{2})(\d{2}).gif", choice)
    year = int(result.group(1))
    month = int(result.group(2))
    day = int(result.group(3))
    message = f"{calendar.month_name[month]} {day}, {year}."
    await ctx.send(message, file=discord.File(choice))


@bagelbot.command(help="Record that funny thing someone said that one time.")
async def quote(ctx, user: discord.User = None, *message):
    quotes = get_param(f"{ctx.guild}_quotes", [])
    if user and not message:
        await ctx.send("Good try! I can't record an empty quote, though.")
        return
    if message:
        quotes.append({"msg": " ".join(message), "author": user.name, "quoted": 0})
        set_param(f"{ctx.guild}_quotes", quotes)
        await ctx.send(f"{user.name} has been recorded for posterity.")
        return
    if not quotes:
        await ctx.send("No quotes! Record a quote using this command.")
        return
    num_quoted = [x["quoted"] for x in quotes]
    qmin = min(num_quoted)
    qmax = max(num_quoted)
    if qmin == qmax:
        w = num_quoted
    else:
        w = [1 - (x - qmin) / (qmax - qmin) + 0.5 for x in num_quoted]
    i = random.choices(range(len(quotes)), weights=w, k=1)[0]
    author = quotes[i]["author"]
    msg = quotes[i]["msg"]
    quotes[i]["quoted"] += 1
    set_param(f"{ctx.guild}_quotes", quotes)
    num_quoted = [x["quoted"] for x in quotes]
    await ctx.send(f"\"{msg}\" - {author}")


@bagelbot.command()
async def join(ctx):
    if not ctx.author.voice:
        await ctx.send("You're not in a voice channel!")
        return
    channel = ctx.author.voice.channel
    await channel.connect()


@bagelbot.command()
async def leave(ctx):
    if not ctx.voice_client:
        await ctx.send("Not connected to voice!")
        return
    await ctx.voice_client.disconnect()


@bagelbot.command(help="This plays the sound Yoda makes in LEGO Star Wars when he dies.")
async def play(ctx):
    voice = get(bagelbot.voice_clients, guild=ctx.guild)
    if not voice:
        await ctx.send("Can't play music before joining a voice channel. Use `join` first.")
        return
    sources = os.listdir("mp3/")
    print(sources)
    src = os.path.abspath("mp3/" + random.choice(sources))
    print(src)
    voice.play(discord.FFmpegPCMAudio(executable=FFMPEG_EXECUTABLE, source=src))
    voice.volume = 100
    voice.is_playing()


@bagelbot.command(help="Make Bagelbot speak to you.")
async def say(ctx, *message):
    voice = get(bagelbot.voice_clients, guild=ctx.guild)
    if not voice:
        await ctx.send("Can't say things before joining a voice channel. Use `join` first.")
        return
    engine.save_to_file(" ".join(message), "voice.mp3")
    engine.runAndWait()
    voice.play(discord.FFmpegPCMAudio(executable=FFMPEG_EXECUTABLE, source="voice.mp3"))
    voice.volume = 100
    voice.is_playing()


@bagelbot.event
async def on_message(message):
    if message.author == bagelbot.user:
        return
    birthday_dialects = ["birth", "burf", "smeef", "smurf", "smith", "name"]
    to_mention = message.author.mention
    if message.mentions:
        to_mention = message.mentions[0].mention
    cleaned = message.content.strip().lower()
    for dialect in birthday_dialects:
        if dialect in cleaned:
            await message.channel.send(f"Happy {dialect}day, {to_mention}!")
            break
    await bagelbot.process_commands(message)
    

@bagelbot.event
async def on_ready():
    print("Connected.")
    log.info("Connected.")
    await update_status()


@bagelbot.event
async def on_command_error(ctx, e):
    await ctx.send(f"Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    bagelbot.run(get_param("DISCORD_TOKEN"))
