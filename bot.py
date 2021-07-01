#! /usr/bin/env python3

print("Starting bagelbot...")

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
from discord.ext import tasks, commands
from discord.utils import get
from discord import FFmpegPCMAudio
from gtts import gTTS
import picamera
import imageio
from subprocess import call
from functools import partial

# from stegano import lsb
# from textgenrnn import textgenrnn # future maybe


YAML_PATH = "bagelbot_state.yaml"

logging.basicConfig(filename=f"{os.path.dirname(__file__)}/log.txt",
    level=logging.INFO, format="%(levelname)-10s %(asctime)-25s %(name)-22s %(funcName)-18s // %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("bagelbot")
log.setLevel(logging.DEBUG)

log.info("STARTING. =============================")


async def schedule_task(time, func):
    now = datetime.now()
    delta = time - now
    if delta < timedelta(seconds=0):
        log.warning(f"Scheduled time ({time}) is before current ({now})!")
    await asyncio.sleep(delta.total_seconds())
    await func()


async def repeat_task(delta, func):
    print(f"Repeating: {func}")
    start = datetime.now()
    while True:
        await schedule_task(start + delta, func)
        start += delta


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


def is_wade(ctx):
    return ctx.message.author.id == 235584665564610561


def wade_only():
    def predicate(ctx):
        log.info(ctx.message.author.id)
        return is_wade(ctx)
    return commands.check(predicate)


async def update_status(bot):
    try:
        bagels = get_param("num_bagels", 0)
        prefix = "anti" if bagels < 0 else ""
        act = discord.Activity(type=discord.ActivityType.watching,
                               name=f" {abs(bagels):0.2f} {prefix}bagels")
        await bot.change_presence(activity=act)
    except Exception:
        pass


def soundify_text(text):
    tts = gTTS(text=text, lang="en")
    filename = stamped_fn("say", "mp3")
    tts.save(filename)
    return discord.FFmpegPCMAudio(executable="/usr/bin/ffmpeg",
           source=filename, options="-loglevel panic")


async def join_voice(bot, ctx, channel):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if not voice or voice.channel != channel:
        if voice:
            await voice.disconnect()
        await channel.connect()


async def ensure_voice(bot, ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if ctx.author.voice:
        await join_voice(bot, ctx, ctx.author.voice.channel)
        return
    options = [x for x in ctx.guild.voice_channels if len(x.voice_states) > 0]
    if not options:
        options = ctx.guild.voice_channels
        if not options:
            return
    choice = random.choice(options)
    await join_voice(bot, ctx, choice)


def stamped_fn(prefix, ext, dir="/home/pi/.bagelbot"):
    if not os.path.exists(dir):
        os.mkdir(dir)
    return f"{dir}/{prefix}-{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.{ext}"


def download_file(url, destination):
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) " \
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    response = requests.get(url, headers=headers)
    bin = response.content
    file = open(destination, "wb")
    file.write(bin)
    file.close()


class Debug(commands.Cog):

    def __init__(self):
        self.hash = hashlib.md5(open(__file__, "r").read().encode("utf-8")).hexdigest()[:8]
        self.startup = datetime.now()

    @commands.command(help="Get current version of this BagelBot.")
    async def version(self, ctx):
        await ctx.send(f"Firmware MD5 {self.hash}; started at " \
            f"{self.startup.strftime('%I:%M:%S %p on %B %d, %Y EST')}")

    @commands.command(help="Download the source code for this bot.")
    async def source(self, ctx):
        url = "https://github.com/jwade109/bagelbot"
        await ctx.send(url, file=discord.File(__file__))

    @commands.command(name="good-bot", help="Tell BagelBot it's doing a good job.")
    async def good_bot(self, ctx):
        reports = get_param("kudos", 0)
        set_param("kudos", reports + 1)
        await ctx.send("Thanks.")

    @commands.command(name="bad-bot", help="Tell BagelBot it sucks.")
    async def bad_bot(self, ctx):
        reports = get_param("reports", 0)
        set_param("reports", reports + 1)
        await ctx.send("Wanker.")

    @commands.command(help="Check Raspberry Pi SD card utilization.")
    async def memory(self, ctx):
        total, used, free = shutil.disk_usage("/")
        await ctx.send(f"{used/2**30:0.3f} GB used; {free/2**30:0.3f} GB free ({used/total*100:0.1f}%)")

    @commands.command(help="Throw an error for testing.")
    async def error(self, ctx):
        raise Exception("This is a fake error for testing.")

    @commands.command(help="Test for limited permissions.")
    @wade_only()
    async def only_wade(self, ctx):
        await ctx.send("Wanker.")


import math

class Bagels(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.DEFAULT_ACCOUNT_BALANCE = 10
        self.DEFAULT_BAGEL_PRICE = 2.50
        self.propagate_bagel_dynamics.start()

    @tasks.loop(minutes=2)
    async def propagate_bagel_dynamics(self):
        bagels = get_param("num_bagels", 0)
        im_bagels = get_param("num_im_bagels", 0)
        mag = math.sqrt(bagels**2 + im_bagels**2)
        arg = math.atan2(im_bagels, bagels)
        arg += 0.002
        bagels = math.cos(arg)*mag
        im_bagels = math.sin(arg)*mag
        set_param("num_bagels", bagels)
        set_param("num_im_bagels", im_bagels)
        log.debug(f"There are now {bagels}+{im_bagels}i bagels.")
        await update_status(self.bot)

    @commands.command(name="bake-bagel", help="Bake a bagel.")
    async def bake_bagel(self, ctx):
        bagels = int(get_param("num_bagels", 0))
        new_bagels = bagels + 1
        set_param("num_bagels", new_bagels)
        if new_bagels == 1:
            await ctx.send(f"There is now {new_bagels} bagel.")
        elif new_bagels == 69:
            await ctx.send(f"There are now {new_bagels} bagels. Nice.")
        else:
            await ctx.send(f"There are now {new_bagels} bagels.")
        await update_status(self.bot)

    @commands.command(help="Check how many bagels there are.")
    async def bagels(self, ctx):
        bagels = int(get_param("num_bagels", 0))
        if bagels == 1:
            await ctx.send(f"There is {bagels} lonely bagel.")
        elif bagels == 69:
            await ctx.send(f"There are {bagels} bagels. Nice.")
        else:
            await ctx.send(f"There are {bagels} bagels.")
        await update_status(self.bot)

    @commands.command(name="eat-bagel", help="Eat a bagel.")
    async def eat_bagel(self, ctx):
        bagels = int(get_param("num_bagels", 0))
        new_bagels = bagels - 1
        set_param("num_bagels", new_bagels)
        if new_bagels == 1:
            await ctx.send(f"There is now {new_bagels} bagel left.")
        elif new_bagels == 69:
            await ctx.send(f"There are now {new_bagels} bagels left. Nice.")
        else:
            await ctx.send(f"There are now {new_bagels} bagels left.")
        await update_status(self.bot)


class Voice(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Leave voice chat.")
    async def leave(self, ctx):
        if not ctx.voice_client:
            await ctx.send("Not connected to voice!")
            return
        await ctx.voice_client.disconnect()

    @commands.command(help="Join voice chat.")
    async def join(self, ctx):
        await ensure_voice(self.bot, ctx)

    @commands.command(help="Make Bagelbot speak to you.")
    async def say(self, ctx, *message):
        await ensure_voice(self.bot, ctx)
        if not message:
            message = ["The lawnmower goes shersheeeeeeerrerererereeeerrr ",
                       "vavavoom sherererererere ruuuuuuuusususususkuskuskuksuksuus"]
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if not voice:
            if not ctx.author.voice:
                await ctx.send("You're not in a voice channel!")
                return
            channel = ctx.author.voice.channel
            await channel.connect()
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        audio = soundify_text(" ".join(message))
        voice.play(audio)

    @commands.command(help="Bagelbot has a declaration to make.")
    async def declare(self, ctx, *message):
        await ensure_voice(self.bot, ctx)
        if not message:
            message = ["Save the world. My final message. Goodbye."]
        if len(message) == 1 and message[0] == "bankruptcy":
            message = ["I. Declare. Bankruptcy!"]
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if not voice:
            if not ctx.author.voice:
                await ctx.send("You're not in a voice channel!")
                return
            channel = ctx.author.voice.channel
            await channel.connect()
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        audio = soundify_text(" ".join(message))
        voice.play(audio)
        while voice.is_playing():
            await asyncio.sleep(0.1)
        await voice.disconnect()

    # @commands.command(help="You're very mature.")
    async def fart(self, ctx):
        FART_DIRECTORY = "farts"
        files = os.listdir(FART_DIRECTORY)
        if not files:
            await ctx.send("I'm not gassy right now!")
            return
        choice = f"{FART_DIRECTORY}/{random.choice(files)}"
        await ensure_voice(self.bot, ctx)
        voice = get(self.bot.voice_clients, guild=ctx.guild)
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

    @commands.command(help="JUUUAAAAAAANNNNNNNNNNNNNNNNNNNNNNNNNN SOTOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO")
    async def soto(self, ctx):
        await ctx.send(file=discord.File("soto.png"))
        await self.declare(ctx, "Juan Soto")

    @commands.command(help="GET MOBIUS HIS JET SKI")
    async def wow(self, ctx):
        await ensure_voice(self.bot, ctx)
        audio = discord.FFmpegPCMAudio(executable="/usr/bin/ffmpeg",
           source="wow.mp3", options="-loglevel panic")
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if not voice:
            if not ctx.author.voice:
                await ctx.send("You're not in a voice channel!")
                return
            channel = ctx.author.voice.channel
            await channel.connect()
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        voice.play(audio)
        



class Miscellaneous(commands.Cog): 

    @commands.command(help="Get the definition of a word.")
    async def define(self, ctx, word: str):
        meaning = PyDictionary().meaning(word)
        if not meaning:
            await ctx.send(f"Sorry, I couldn't find a definition for '{word}'.")
            return
        ret = f">>> **{word.capitalize()}:**"
        for key, value in meaning.items():
            ret += f"\n ({key})"
            for i, v in enumerate(value):
                ret += f"\n {i+1}. {v}"
        await ctx.send(ret)

    @commands.command(help="Get a picture of an animal and a fun fact about it.")
    async def animal(self, ctx, animal_type: str = ""):
        accepted_types = "cat dog panda koala fox racoon kangaroo".split(" ")
        if animal_type not in accepted_types:
            await ctx.send(f"'{animal_type}' is not a supported animal type; acceptable " \
                f"types are {', '.join(accepted_types)}.")
        animal = Animals(animal_type)
        url = animal.image()
        fact = animal.fact()
        await ctx.send(f"{fact}\n{url}")

    @commands.command(help="Perform mathy math on two numbers.")
    async def math(self, ctx, a: int, op: str, b: int):
        if op not in ["+", "-", "*", "/"]:
            await ctx.send("Error: {op} is not a supported math operator.")
        s = a + b + random.randint(-12, 9)
        await ctx.send(f"{a} {op} {b} = {s}. Thanks for playing.")

    @commands.command(help="Use a moose to express your thoughts.")
    async def moose(self, ctx, *message):
        cheese = cow.Moose()
        msg = cheese.milk(" ".join(message))
        await ctx.send(f"```\n{msg}\n```")

    @commands.command(help="Add two numbers better than previously thought possible.")
    async def badmath(self, ctx, a: int, b: int):
        await ctx.send(f"{a} + {b} = {str(a) + str(b)}. Thanks for playing.")

    @commands.command(help="Roll a 20-sided die.")
    async def d20(self, ctx):
        roll = random.randint(1, 20)
        if roll == 20:
            await ctx.send(f"Rolled a 20! :confetti_ball:")
        else:
            await ctx.send(f"Rolled a {roll}.")

    @commands.command(help="Say hi!")
    async def hello(self, ctx):
        await ctx.send(f"Hey, {ctx.author.name}, it me, ur bagel.")

    @commands.command(name="dean-winchester", help="It's Dean Winchester, from Lost!")
    async def dean_winchester(self, ctx):
        await ctx.send(file=discord.File("dean.gif"))

    @commands.command(help="Ask wikipedia for things.")
    async def wikipedia(self, ctx, query: str):
        await ctx.send(wiki.summary(query))

    @commands.command(help="Get info about a pokemon by its name.", category="pokemon")
    async def pokedex(self, ctx, id: int = None):
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

    @commands.command(help="Get info about a pokemon by Pokedex ID.", category="pokemon")
    async def pokemon(self, ctx, name: str = None):
        if not name:
            await self.pokedex(ctx, None)
            return
        try:
            p = pypokedex.get(name=name)
        except:
            await ctx.send(f"Pokemon `{name}` was not found.")
        await self.pokedex(ctx, p.dex)

    @commands.command(name="rocket-league", help="Make BagelBot play Rocket League.")
    async def rocket_league(self, ctx):
        await ctx.send("PINCH.")

    @commands.command(help="Bepis.")
    async def bepis(self, ctx):
        await ctx.send("m" * random.randint(3, 27) + "bepis.")

    @commands.command(help="Drop some hot Bill Watterson knowledge.")
    async def ch(self, ctx):
        files = [os.path.join(path, filename)
                 for path, dirs, files in os.walk("ch")
                 for filename in files
                 if filename.endswith(".gif")]
        choice = random.choice(files)
        result = re.search(r".+(\d{4})(\d{2})(\d{2}).gif", choice)
        year = int(result.group(1))
        month = int(result.group(2))
        day = int(result.group(3))
        message = f"{calendar.month_name[month]} {day}, {year}."
        await ctx.send(message, file=discord.File(choice))

    @commands.command(help="Record that funny thing someone said that one time.")
    async def quote(self, ctx, user: discord.User = None, *message):
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


class Camera(commands.Cog):

    def __init__(self, bot, camera, still, video):
        self.bot = bot
        self.STILL_RESOLUTION = still
        self.VIDEO_RESOLUTION = video
        self.camera = camera
        self.timelapse_active = False
        self.last_still_capture = None
        # self.video_in_the_morning.start()

    @tasks.loop()
    async def video_in_the_morning(self):
        now = datetime.now()
        if now.hour > 6 and now.hour < 10:
            await self.take_video(stamped_fn("autocap", "h264"), 30*60)
        else:
            await asyncio.sleep(60)

    def take_still(self, filename):
        log.debug(f"Writing camera capture to {filename}.")
        self.camera.resolution = self.STILL_RESOLUTION
        self.camera.capture(filename) 

    async def take_video(self, filename, seconds):
        log.debug(f"Writing camera capture ({seconds} seconds) to {filename}.")
        self.camera.resolution = self.VIDEO_RESOLUTION
        self.camera.start_recording(filename)
        await asyncio.sleep(seconds+1)
        self.camera.stop_recording()
        log.debug(f"Done: {filename}.")

    @commands.command(help="Look through Bagelbot's eyes.")
    async def capture(self, ctx, seconds: float = None):
        if not seconds:
            filename = stamped_fn("cap", "jpg")
            self.take_still(filename)
            await ctx.send(file=discord.File(filename))
            return
        if seconds > 60 and not is_wade(ctx):
            await ctx.send("I don't support capture durations greater than 60 seconds.")
            return
        await ctx.send(f"Recording for {seconds} seconds.")
        filename = stamped_fn("cap", "h264")
        await ctx.send(f"`scp pi@spookyscary.ddns.net:{filename} .`")
        await self.take_video(filename, seconds)
        await ctx.send("Done.")
        # await ctx.send(file=discord.File(filename))

    # @commands.command(name="timelapse-start", help="Start timelapse.")
    async def timelapse_start(self, ctx):
        log.debug("Enabling timelapse capture.")
        self.timelapse_active = True
        await ctx.send("timelapse_active = True")

    # @commands.command(name="timelapse-stop", help="Stop timelapse.")
    async def timelapse_stop(self, ctx):
        log.debug("Disabling timelapse capture.")
        self.timelapse_active = False
        await ctx.send("timelapse_active = False")


def main():

    STILL_RES = (3280, 2464)
    VIDEO_RES = (1080, 720)
    pi_camera = picamera.PiCamera()

    bagelbot = commands.Bot(command_prefix=["bagelbot ", "Bagelbot ", "bb ", "$ "])

    @bagelbot.event
    async def on_ready():
        print("Connected.")
        log.info("Connected.")
        await update_status(bagelbot)

    @bagelbot.event
    async def on_command_error(ctx, e):
        errstr = traceback.format_exception(type(e), e, e.__traceback__)
        errstr = "\n".join(errstr)
        s = f"Error: {type(e).__name__}: {e}\n```\n{errstr}\n```"
        await ctx.send(f"Error: {type(e).__name__}: {e}")
        log.error(f"{ctx.message.content}:\n{s}")

    @bagelbot.event
    async def on_message(message):
        if message.author == bagelbot.user:
            return
        log.debug(f"{message.author.name}: {message.content}")
        birthday_dialects = ["birth", "burf", "smeef", "smurf", "smith"]
        to_mention = message.author.mention
        if message.mentions:
            to_mention = message.mentions[0].mention
        cleaned = message.content.strip().lower()
        for dialect in birthday_dialects:
            if dialect in cleaned:
                await message.channel.send(f"Happy {dialect}day, {to_mention}!")
                break
        await bagelbot.process_commands(message)

    @bagelbot.before_invoke
    async def before_invoke(ctx):
        log.debug(str(ctx))

    bagelbot.add_cog(Debug())
    bagelbot.add_cog(Bagels(bagelbot))
    bagelbot.add_cog(Voice(bagelbot))
    bagelbot.add_cog(Camera(bagelbot, pi_camera, STILL_RES, VIDEO_RES))
    bagelbot.add_cog(Miscellaneous())
    bagelbot.run(get_param("DISCORD_TOKEN"))


if __name__ == "__main__":
    main()

