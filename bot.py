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

logging.basicConfig(filename="/home/ubuntu/bagelbot/log.txt",
                    level=logging.WARNING, format=LOG_FORMAT,
                    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("bagelbot")
log.setLevel(logging.DEBUG)
client = discord.Client()
all_commands = []
startup = datetime.now()
version_hash = hashlib.md5(open(__file__, "r").read().encode("utf-8")).hexdigest()[:8]
dictionary = PyDictionary()

log.info("STARTING. =============================")

class Context:
    def __init__(self, guild, author, author_name, channel, channel_name, attachments):
        self.guild = guild
        self.author = author
        self.channel = channel
        self.author_name = author_name
        self.channel_name = channel_name
        self.attachments = attachments

    def __repr__(self):
        d = self.__dict__
        vals = ", ".join([f"{k}={v}" for k, v in d.items()])
        return f"<context {vals}>"

    def __str__(self):
        return self.__repr__()


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


async def logchannel(channel, string, shhh=False):
    if channel is None:
        log.info(string)
    else:
        log.info(f"({channel.name}) {string}")
    if not shhh:
        print(f"[{datetime.now()}] [LOCAL] {string}")
    if not OFFLINE:
        await channel.send(string)


async def send_file(path, channel):
    file = open(str(path), "rb")
    print(f"[{datetime.now()}] [LOCAL] {path}")
    if not OFFLINE:
        await channel.send(file=discord.File(file))


async def logdebug(string, guild):
    print(f"[{datetime.now()}] [DEBUG] {string}")
    if not OFFLINE:
        channel = get_debug_channel(guild)
        if channel:
            await logchannel(channel, string, True)


def suggest_command(misspelled):
    to_beat = float("-inf")
    best = None
    # matches = []
    for cmd in all_commands:
        name = cmd.__name__.replace("_", "-")
        dist = editdistance.eval(name, misspelled)
        score = 1 - (dist / max(len(misspelled), len(name)))
        if score > to_beat:
            best = name
            to_beat = score
    #     matches.append((name, score))
    # matches.sort(key=lambda x: 1 - x[1])
    # for name, score in matches:
    #     print(f"{name}: {score*100:0.0f}%")
    if to_beat < 0.5:
        return None
    return f"{best}"


def command(func):
    log.debug(f"{func.__name__} registered as bagelbot command.")
    all_commands.append(func)
    all_commands.sort(key=lambda x: x.__name__)
    return func


@command
def version():
    """Get current version of this BagelBot."""
    return f"Firmware MD5 {version_hash}; started at {startup.strftime('%I:%M:%S %p on %B %d, %Y EST')}", None


@command
def help(command: str):
    """Get information about a particular command."""
    docstrs = {}
    for f in all_commands:
        docstrs[f.__name__.replace("_", "-")] = \
                f.__doc__ if f.__doc__ else "No help documentation for this command."
    if command not in docstrs:
        return f"'{command}' is not a command name. Are you ok?", None
    return f"{docstrs[command]}", None


@command
def define(word: str):
    """Get the definition of a word."""
    meaning = dictionary.meaning(word)
    if not meaning:
        return f"Sorry, I couldn't find a definition for '{word}'.", None
    ret = f">>> **{word.capitalize()}:**"
    for key, value in meaning.items():
        ret += f"\n ({key})"
        for i, v in enumerate(value):
            ret += f"\n {i+1}. {v}"
    return ret, None


@command
def soto():
    """JUUUAAAAAAANNNNNNNNNNNNNNNNNNNNNNNNNN SOTOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO"""
    return Path(JUAN_SOTO), None


@command
def animal(animal_type: str = ""):
    """Get a picture of an animal and a fun fact about it."""
    accepted_types = "cat dog panda koala fox racoon kangaroo".split(" ")
    if animal_type not in accepted_types:
        return f"'{animal_type}' is not a supported animal type; acceptable " \
               f"types are {', '.join(accepted_types)}.", None
    animal = Animals(animal_type)
    url = animal.image()
    fact = animal.fact()
    return f"{fact}\n{url}", None


@command
def math(a: int, op: str, b: int):
    """Perform mathy math on two numbers."""
    if op not in ["+", "-", "*", "/"]:
        return f"Error: {op} is not a supported math operator.", None
    sum = a + b + random.randint(-12, 9)
    return f"{a} {op} {b} = {sum}. Thanks for playing.", None


@command
def moose(message: str = ""):
    """Use a moose to express your thoughts."""
    cheese = cow.Moose()
    msg = cheese.milk(message)
    return f"```\n{msg}\n```", None


@command
def list_commands():
    """Print commands."""
    ret = "```\n"
    for cmd in all_commands:
        sig = []
        for k, v in signature(cmd).parameters.items():
            if v.annotation != Context:
                sig.append(f"[{k}: {v.annotation.__name__}]")
        sig = " ".join(sig)
        doc = cmd.__doc__
        if not doc:
            doc = "(No docstring for this command.)"
        ret += f"{cmd.__name__.replace('_', '-'):<20}"
               # f"    {sig:<35}    {doc}\n"
    ret += "```"
    return ret, None


@command
def badmath(a: int, b: int):
    """Add two numbers better than previously thought possible."""
    return f"{a} + {b} = {str(a) + str(b)}. Thanks for playing.", None


@command
def d20():
    """Roll a 20-sided die."""
    roll = random.randint(1, 20)
    if roll == 20:
        return f"Rolled a 20! :confetti_ball:", None
    return f"Rolled a {roll}.", None


@command
def source():
    """Download the source code for this bot."""
    return ["https://github.com/jwade109/bagelbot",
             Path(os.path.abspath(__file__))], None


@command
def hello():
    """Say hi!"""
    return f"Hey, it me, ur bagel.", None


@command
def dean_winchester():
    """It's Dean Winchester, from Lost!"""
    return Path(os.path.abspath("dean.gif")), None


@command
def wikipedia(query: str):
    """Ask wikipedia for things."""
    result = wiki.summary(query)
    return result, None


@command
def bake_bagel():
    """Add a bagel to the bagel pile."""
    bagels = get_param("num_bagels", 0)
    new_bagels = bagels + 1
    set_param("num_bagels", new_bagels)
    if new_bagels == 1:
        return f"There is now {new_bagels} bagel.", None
    if new_bagels == 69:
        return f"There are now {new_bagels} bagels. Nice.", None
    return f"There are now {new_bagels} bagels.", None


@command
def bagels():
    """Check how many bagels there are."""
    bagels = get_param("num_bagels", 0)
    if bagels == 1:
        return f"There is {bagels} lonely bagel.", None
    if bagels == 69:
        return f"There are {bagels} bagels. Nice.", None
    return f"There are {bagels} bagels.", None


@command
def eat_bagel():
    """Eat a bagel."""
    bagels = get_param("num_bagels", 0)
    if bagels == 0:
        return "There are no more bagels!", None
    new_bagels = bagels - 1
    set_param("num_bagels", new_bagels)
    if new_bagels == 1:
        return f"There is now {new_bagels} bagel left.", None
    if new_bagels == 69:
        return f"There are now {new_bagels} bagels left. Nice.", None
    return f"There are now {new_bagels} bagels left.", None


@command
def good_bot():
    """Tell BagelBot it's doing a good job."""
    reports = get_param("kudos", 0)
    set_param("kudos", reports + 1)
    return "Thanks!", "BagelBot has been commended for good behavior."


@command
def bad_bot():
    """Tell BagelBot it sucks."""
    reports = get_param("reports", 0)
    set_param("reports", reports + 1)
    return "Wanker.", "BagelBot has been reported for bad behavior."


@command
def pokedex(id: int):
    """Get info about a Pokemon given its Pokedex ID."""
    if id is None:
        id = random.randint(1, 898)
    if id > 898:
        return "There are only 898 pokemon.", None
    if id < 1:
        return "Only takes numbers greater than zero.", None
    try:
        p = pypokedex.get(dex=id)
    except:
        return f"Pokemon `{name}` was not found.", None
    return [f"{p.name.capitalize()} ({p.dex}). " \
           f"{', '.join([x.capitalize() for x in p.types])} type. " \
           f"{p.weight/10} kg. {p.height/10} m.",
           f"https://assets.pokemon.com/assets/cms2/img/pokedex/detail/{str(id).zfill(3)}.png"], None


@command
def pokemon(name: str):
    try:
        p = pypokedex.get(name=name)
    except:
        return f"Pokemon `{name}` was not found.", None
    return pokedex(p.dex)


@command
def rocket_league():
    """Make BagelBot play Rocket League."""
    return "PINCH.", None


@command
def bepis():
    """Bepis."""
    return "m" * random.randint(3, 27) + "bepis.", None


# @command
def encode(ctx: Context, message: str):
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


# @command
def decode(ctx: Context):
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

@command
def ch():
    """Get a random 'Calvin and Hobbes' comic strip."""
    files = [os.path.join(path, filename)
             for path, dirs, files in os.walk(CALVIN_AND_HOBBES_DIR)
             for filename in files
             if filename.endswith(".gif")]
    choice = random.choice(files)
    print(choice)
    result = re.search(r".+(\d{4})(\d{2})(\d{2}).gif", choice)
    year = int(result.group(1))
    month = int(result.group(2))
    day = int(result.group(3))
    message = f"{calendar.month_name[month]} {day}, {year}."
    filename = Path(os.path.abspath(choice))
    return [message, filename], None


@command
def quoteme(ctx: Context, message: str):
    quotes = get_param(f"{ctx.guild}_quotes", [])
    quotes.append({"msg": message, "author": ctx.author})
    set_param(f"{ctx.guild}_quotes", quotes);
    return "You have been recorded for posterity.", None


@command
def quote(ctx: Context):
    quotes = get_param(f"{ctx.guild}_quotes", [])
    num_quoted = [x["quoted"] for x in quotes]
    print(num_quoted)
    qmin = min(num_quoted)
    qmax = max(num_quoted)
    if qmin == qmax:
        w = num_quoted
    else:
        w = [1 - (x - qmin) / (qmax - qmin) + 0.5 for x in num_quoted]
    print(", ".join([f"{x:0.2f}" for x in w]))
    i = random.choices(range(len(quotes)), weights=w, k=1)[0]
    author = quotes[i]["author"]
    msg = quotes[i]["msg"]
    quotes[i]["quoted"] += 1
    set_param(f"{ctx.guild}_quotes", quotes)
    num_quoted = [x["quoted"] for x in quotes]
    print(num_quoted)
    return f"\"{msg}\" - <@{author}>", None


def handle(ctx, message):
    tokens = message.split(" ")
    if not tokens:
        return None, None
    command = tokens[0].lower()
    if not command:
        command = "hello"
    argin = tokens[1:]
    to_execute = None
    for cmd in all_commands:
        name = cmd.__name__.replace("_", "-")
        if command == name:
            to_execute = cmd
    if not to_execute:
        suggested = suggest_command(command)
        if suggested:
            return f"Couldn't find command `{command}`. " \
                   f"Did you mean `{suggested}`?", None
        return f"Couldn't find command `{command}`. " \
               f"Use `bagelbot list-commands` to view available commands." , None

    sig = list(signature(to_execute).parameters.values())
    expected = len(sig)
    actual = len(argin)

    argout = []
    print(ctx)
    print(message)
    if expected > 0 and sig[0].annotation == Context:
        argout.append(ctx)
        expected -= 1
        sig = sig[1:]

    if actual > expected:
        argin[expected - 1] = " ".join(argin[expected-1:])

    for i, t in enumerate(sig):
        if i >= len(argin):
            continue
        try:
            argout.append(t.annotation(argin[i]))
        except:
            return f"Expected argument {i+1}, '{argin[i]}', to be of " \
                   f"type {t.annotation.__name__}.", None
    if not argout:
        return to_execute()
    else:
        return to_execute(*argout)


async def do_message(text, author_id, author_name, channel, channel_id, channel_name, guild, attach):
    log.info(f"({channel_name}, {author_name}) {text}")
    lowercase = text.lower()
    if lowercase.startswith("bagelbot"):
        text = text[len("bagelbot"):].strip()
    elif lowercase.startswith("🥯"):
        text = text[len("🥯"):].strip()
    elif text.startswith("<:wade:499740446185226261>"):
        text = text[len("<:wade:499740446185226261>"):].strip()
    else:
        return

    ctx = Context(guild, author_id, author_name, channel_id, channel_name, attach);

    try:
        result, error = handle(ctx, text)
        if result and not isinstance(result, list):
            result = [result]
        for res in result:
            if res and isinstance(res, str):
                await logchannel(channel, res)
            if res and isinstance(res, Path):
                await send_file(res, channel)
        if error:
            await logdebug(error, guild)
    except Exception as e:
        await logchannel(channel, f"Oh, shit! An exception occurred: {e}");
        errstr = traceback.format_exc()
        await logdebug(f"An exception was thrown while handling '{text}':\n```\n{errstr}```", guild)
    await update_status()


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    cleaned = message.content.strip()
    await do_message(cleaned, message.author.id, message.author.name, message.channel, message.channel.id, message.channel.name, message.guild, message.attachments)


async def main():
    to_parse = " ".join(sys.argv[1:])
    await do_message(to_parse, "AUTHOR_ID", "AUTHOR_NAME", None, "CHANNEL_ID", "CHANNEL_NAME", "GUILD", [])


async def update_status():
    if OFFLINE:
        return
    bagels = get_param("num_bagels", 0)
    act = discord.Activity(type=discord.ActivityType.watching,
                           name=f" {bagels} bagels")
    await client.change_presence(activity=act)


@client.event
async def on_ready():
    version_info, _ = version()
    s = f"Connected. ({version_info})"
    print(s)
    log.info(s)
    await update_status()



if __name__ == "__main__":
    if len(sys.argv) > 1:
        OFFLINE = True
        log.info("Running in OFFLINE mode.")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
        loop.close()
    else:
        log.info("Running in ONLINE mode.")
        client.run(get_param("DISCORD_TOKEN"))
