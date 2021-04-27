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
from datetime import datetime, timedelta
import calendar
import hashlib
import signal
import sys
import shutil
from PyDictionary import PyDictionary
import wikipedia as wiki
import pypokedex
import editdistance
import wget
import requests
from discord.ext.commands import Bot
from discord.utils import get
from discord import FFmpegPCMAudio
from gtts import gTTS
import picamera
import imageio
from subprocess import call
from functools import partial

# from stegano import lsb
# from textgenrnn import textgenrnn # future maybe

TEMP_DIR = "/home/pi/.bagelbot"
if not os.path.exists(TEMP_DIR):
    os.mkdir(TEMP_DIR)

LOG_FORMAT = "%(levelname)-10s %(asctime)-25s %(name)-22s %(funcName)-18s // %(message)s"
YAML_PATH = "bagelbot_state.yaml"

MOZILLA_HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) " \
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
CALVIN_AND_HOBBES_DIR = "ch/"
JUAN_SOTO = "soto.png"
FFMPEG_EXECUTABLE = "C:\\ffmpeg\\bin\\ffmpeg.exe"

STILL_RESOLUTION = (3280, 2464)
VIDEO_RESOLUTION = (720, 480)
pi_camera = picamera.PiCamera()

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


def stamped_fn(prefix, ext):
    return f"{TEMP_DIR}/{prefix}-{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.{ext}"


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


async def update_status():
    bagels = get_param("num_bagels", 0)
    prefix = "anti" if bagels < 0 else ""
    act = discord.Activity(type=discord.ActivityType.watching,
                           name=f" {abs(bagels)} {prefix}bagels")
    await bagelbot.change_presence(activity=act)


@bagelbot.command(help="Get current version of this BagelBot.")
async def version(ctx):
    await ctx.send(f"Firmware MD5 {version_hash}; started at " \
        f"{startup.strftime('%I:%M:%S %p on %B %d, %Y EST')}")


@bagelbot.command(help="Get the definition of a word.")
async def define(ctx, word: str):
    meaning = dictionary.meaning(word)
    if not meaning:
        await ctx.send(f"Sorry, I couldn't find a definition for '{word}'.")
        return
    ret = f">>> **{word.capitalize()}:**"
    for key, value in meaning.items():
        ret += f"\n ({key})"
        for i, v in enumerate(value):
            ret += f"\n {i+1}. {v}"
    await ctx.send(ret)


@bagelbot.command(help="JUUUAAAAAAANNNNNNNNNNNNNNNNNNNNNNNNNN SOTOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO")
async def soto(ctx):
    await ctx.send(file=discord.File(JUAN_SOTO))
    await declare(ctx, "Juan Soto")


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
    elif new_bagels == 69:
        await ctx.send(f"There are now {new_bagels} bagels. Nice.")
    else:
        await ctx.send(f"There are now {new_bagels} bagels.")
    await update_status()


@bagelbot.command(help="Check how many bagels there are.")
async def bagels(ctx):
    bagels = get_param("num_bagels", 0)
    if bagels == 1:
        await ctx.send(f"There is {bagels} lonely bagel.")
    elif bagels == 69:
        await ctx.send(f"There are {bagels} bagels. Nice.")
    else:
        await ctx.send(f"There are {bagels} bagels.")
    await update_status()


@bagelbot.command(name="eat-bagel", help="Eat a bagel.")
async def eat_bagel(ctx):
    bagels = get_param("num_bagels", 0)
    # if bagels == 0:
        # await ctx.send("There are no more bagels!")
        # await update_status()
        # return
    new_bagels = bagels - 1
    set_param("num_bagels", new_bagels)
    if new_bagels == 1:
        await ctx.send(f"There is now {new_bagels} bagel left.")
    elif new_bagels == 69:
        await ctx.send(f"There are now {new_bagels} bagels left. Nice.")
    else:
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


@bagelbot.command(help="Throw an error for testing.")
async def error(ctx):
    raise Exception("This is a fake error for testing.")


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
    attach = ctx.attachments[0]
    filename = f"{TEMP_DIR}/encode-{attach.filename}".replace(".jpg", ".png")
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
    attach = ctx.attachments[0]
    filename = f"{TEMP_DIR}/decode-{attach.filename}".replace(".jpg", ".png")
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


async def remind_user(ctx, message):
    await ctx.send(f"{ctx.author.mention}, you asked me to remind you to **{message}**.")


class DateTime(discord.ext.commands.Converter):
    async def convert(self, ctx, argument):
        ret = datetime.now() + timedelta(minutes=int(argument))
        return ret


@bagelbot.command(help="Ask Bagelbot to remind you of something in the future.")
async def remindme(ctx, time: DateTime, *message):
    if not message:
        await ctx.send("Please provide a message to remind you of.")
        return
    message = " ".join(message)
    await ctx.send(f"Ok, I'll remind you to **{message}** at {time.strftime('%I:%M %p on %B %d, %Y EST')}.")
    await schedule_task(time, partial(remind_user, ctx, message))


@bagelbot.command()
async def memory(ctx):
    total, used, free = shutil.disk_usage("/")
    await ctx.send(f"{used/2**30:0.3f} GB used; {free/2**30:0.3f} GB free ({used/total*100:0.1f}%)")


@bagelbot.command()
async def leave(ctx):
    if not ctx.voice_client:
        await ctx.send("Not connected to voice!")
        return
    await ctx.voice_client.disconnect()


def soundify_text(text):
    tts = gTTS(text=text, lang="en", tld="ie")
    filename = stamped_fn("say", "mp3")
    tts.save(filename)
    return discord.FFmpegPCMAudio(executable="/usr/bin/ffmpeg",
           source=filename, options="-loglevel panic")


async def join_voice(ctx, channel):
    voice = get(bagelbot.voice_clients, guild=ctx.guild)
    if not voice or voice.channel != channel:
        if voice:
            await voice.disconnect()
        await channel.connect()


@bagelbot.command()
async def join(ctx):
    await ensure_voice(ctx)


async def ensure_voice(ctx):
    voice = get(bagelbot.voice_clients, guild=ctx.guild)
    if ctx.author.voice:
        await join_voice(ctx, ctx.author.voice.channel)
        return
    options = [x for x in ctx.guild.voice_channels if len(x.voice_states) > 0]
    if not options:
        options = ctx.guild.voice_channels
        if not options:
            return
    choice = random.choice(options)
    await join_voice(ctx, choice)


@bagelbot.command(help="Make Bagelbot speak to you.")
async def say(ctx, *message):
    await ensure_voice(ctx)
    if not message:
        message = ["The lawnmower goes shersheeeeeeerrerererereeeerrr ",
                   "vavavoom sherererererere ruuuuuuuusususususkuskuskuksuksuus"]
    voice = get(bagelbot.voice_clients, guild=ctx.guild)
    if not voice:
        if not ctx.author.voice:
            await ctx.send("You're not in a voice channel!")
            return
        channel = ctx.author.voice.channel
        await channel.connect()
    voice = get(bagelbot.voice_clients, guild=ctx.guild)
    audio = soundify_text(" ".join(message))
    voice.play(audio)


@bagelbot.command(help="Bagelbot has a declaration to make.")
async def declare(ctx, *message):
    await ensure_voice(ctx)
    if not message:
        message = ["Save the world. My final message. Goodbye."]
    if len(message) == 1 and message[0] == "bankruptcy":
        message = ["I. Declare. Bankruptcy!"]
    voice = get(bagelbot.voice_clients, guild=ctx.guild)
    if not voice:
        if not ctx.author.voice:
            await ctx.send("You're not in a voice channel!")
            return
        channel = ctx.author.voice.channel
        await channel.connect()
    voice = get(bagelbot.voice_clients, guild=ctx.guild)
    audio = soundify_text(" ".join(message))
    voice.play(audio)
    while voice.is_playing():
        await asyncio.sleep(0.1)
    await voice.disconnect()


@bagelbot.command(help="You're very mature.")
async def fart(ctx):
    FART_DIRECTORY = "farts"
    files = os.listdir(FART_DIRECTORY)
    if not files:
        await ctx.send("I'm not gassy right now!")
        return
    choice = f"{FART_DIRECTORY}/{random.choice(files)}"
    await ensure_voice(ctx)
    voice = get(bagelbot.voice_clients, guild=ctx.guild)
    if not voice:
        if not ctx.author.voice:
            await ctx.send("You're not in a voice channel!")
            return
        channel = ctx.author.voice.channel
        await channel.connect()
    await ctx.send("*Farts aggressively.*")
    audio = discord.FFmpegPCMAudio(executable="/usr/bin/ffmpeg",
            source=choice, options="-loglevel panic")
    voice.play(audio)


@bagelbot.command(help="Look through Bagelbot's eyes into the horror that is Christiansburg.")
async def capture(ctx, seconds: float = None):
    if not seconds:
        filename = stamped_fn("cap", "jpg")
        log.debug(f"Writing camera capture to {filename}.")
        pi_camera.resolution = STILL_RESOLUTION
        pi_camera.capture(filename)
        await ctx.send(file=discord.File(filename))
        return
    if seconds > 60:
        await ctx.send("I don't support capture durations greater than 60 seconds.")
        return
    filename = stamped_fn("cap", "h264")
    log.debug(f"Writing camera capture ({seconds} seconds) to {filename}.")
    await ctx.send(f"Recording for {seconds} seconds.")
    pi_camera.resolution = VIDEO_RESOLUTION
    pi_camera.start_recording(filename)
    await asyncio.sleep(seconds)
    pi_camera.stop_recording()
    mp4_filename = filename.replace(".h264", ".mp4")
    log.debug(f"Converting to {mp4_filename}.")
    call(["MP4Box", "-add", filename, mp4_filename])
    os.remove(filename)
    await ctx.send(file=discord.File(mp4_filename))


@bagelbot.command(name="timelapse-start", help="Start timelapse.")
async def timelapse_start(ctx):
    log.debug("Enabling timelapse capture.")
    set_param("timelapse_active", True)
    await ctx.send("timelapse_active = True")


@bagelbot.command(name="timelapse-stop", help="Stop timelapse.")
async def timelapse_stop(ctx):
    log.debug("Disabling timelapse capture.")
    set_param("timelapse_active", False)
    await ctx.send("timelapse_active = False")


@bagelbot.event
async def on_message(message):
    if message.author == bagelbot.user:
        return
    log.debug(f"{message.author.name}: {message.content}")
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


async def schedule_task(time, func):
    now = datetime.now()
    delta = time - now
    if delta < timedelta(seconds=0):
        log.warning(f"Scheduled time ({time}) is before current ({now})!")
    await asyncio.sleep(delta.total_seconds())
    await func()


async def repeat_task(delta, func):
    start = datetime.now()
    while True:
        await schedule_task(start + delta, func)
        start += delta


async def capture_frame():
    if not get_param("timelapse_active", False):
        return
    filename = stamped_fn("autocap", "jpg")
    log.debug(f"Writing camera capture to {filename}.")
    pi_camera.resolution = STILL_RESOLUTION
    pi_camera.capture(filename)


@bagelbot.event
async def on_ready():
    print("Connected.")
    log.info("Connected.")
    await update_status()
    now = datetime.now()
    bagelbot.loop.create_task(repeat_task(timedelta(seconds=10), capture_frame))


@bagelbot.event
async def on_command_error(ctx, e):
    s = f"Error: {type(e).__name__}: {e}"
    await ctx.send(s)
    log.error(f"{s}: {ctx.message.content}")


if __name__ == "__main__":
    bagelbot.run(get_param("DISCORD_TOKEN"))
