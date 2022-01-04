#! /usr/bin/env python3

print("Starting bagelbot...")

import os

import sys
import logging

log_filename = "/home/pi/bagelbot/log.txt"
archive_filename = "/home/pi/bagelbot/archive.txt"
logging.basicConfig(filename=log_filename,
    level=logging.WARN, format="%(levelname)-8s %(asctime)s.%(msecs)03d %(name)-12s %(funcName)-26s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("bagelbot")
log.setLevel(logging.DEBUG)

log.info("STARTING. =============================")
log.info(f"Program args: {sys.argv}")
log.info(f"CWD: {os.getcwd()}")
print(f"Writing to {log_filename}")

import discord
import re
import random
import asyncio
import math
from glob import glob
from pathlib import Path
from traceback import format_exception
import yaml
from animals import Animals
from cowpy import cow
from datetime import datetime, timedelta, timezone
import calendar
import shutil
from PyDictionary import PyDictionary
import wikipedia as wiki
import pypokedex
import requests
from discord.ext import tasks, commands
from discord.utils import get
from discord import FFmpegPCMAudio, FFmpegOpusAudio
from gtts import gTTS
import picamera
from fuzzywuzzy import process
from youtube_dl import YoutubeDL
from dataclasses import dataclass, field
from typing import Union
import collections
import socket
import xmlrpc.client
import validators # for checking if string is a URL
from gibberish import Gibberish as gib
gib = gib() # you've got to be kidding me with this object-oriented BS, seriously
import randomname # for generating bug ticket names
import dateutil.parser as dparser # for parsing times from remind args
from dateparser import parse
import itertools
from bs4 import BeautifulSoup # for bacon
from functools import lru_cache # for SW EP3 quote cache

# for chess module
from cairosvg import svg2png
import chess
import chess.svg

# for sunrise and sunset timings
import suntime

# for counting syllables for haiku detection
import curses
from curses.ascii import isdigit
import nltk
from nltk.corpus import cmudict

from farkle import Farkle
from state_machine import get_param, set_param

CMU_DICT = cmudict.dict()

def get_sunrise_today(lat, lon):
    sun = suntime.Sun(lat, lon)
    now = datetime.now()
    return sun.get_local_sunrise_time(now).replace(tzinfo=None)

def request_location():
    log.info("Requesting location from remote...")
    response = requests.get("http://ipinfo.io/json")
    data = response.json()
    loc = [float(x) for x in data['loc'].split(",")]
    log.info(f"Got {loc}.")
    return loc

def get_bacon():
    html = requests.get(f"https://baconipsum.com/?paras={random.randint(1,5)}" \
        "&type=meat-and-filler&start-with-lorem=0").content
    soup = BeautifulSoup(html, 'html.parser')
    ret = soup.find("div", {"class": "anyipsum-output"}).get_text()
    if len(ret) > 1800:
        ret = ret[:1800]
    return ret

def get_wisdom():
    html = requests.get(f"https://fungenerators.com/random/sentence").content
    soup = BeautifulSoup(html, 'html.parser')
    ret = soup.find("h2").get_text()
    if len(ret) > 1800:
        ret = ret[:1800]
    return ret

def detect_haiku(stuff):

    def count_syllables(word):
        low = word.lower()
        if low == "bb":
            return 2
        if low == "bagelbot":
            return 3
        if low not in CMU_DICT:
            log.warning(f"Not found in CMU dictionary: {word}")
            return None
        syl_list = [len(list(y for y in x if isdigit(y[-1]))) for x in CMU_DICT[low]]
        syl_list = list(set(syl_list))
        if len(syl_list) > 1:
            log.warning(f"Ambiguities in the number of syllables of {word}. (Dictionary entry: {CMU_DICT[low]})")
        if not syl_list:
            log.warning(f"Ambiguities in the number of syllables of {word}. (Dictionary entry: {CMU_DICT[low]})")
            return None
        return syl_list[0]

    stuff = stuff.split(" ")
    lens = [count_syllables(x) for x in stuff]
    if None in lens:
        return None
    cumulative = list(itertools.accumulate(lens))
    log.debug(cumulative)
    if cumulative[-1] != 17 or 5 not in cumulative or 12 not in cumulative:
        return None
    first = " ".join(stuff[:cumulative.index(5) + 1])
    second = " ".join(stuff[cumulative.index(5) + 1:cumulative.index(12) + 1])
    third = " ".join(stuff[cumulative.index(12) + 1:])
    return first, second, third

def get_bug_ticket_name():
    return randomname.get_name(adj=('physics'), noun=('dogs')) + \
        "-" + str(random.randint(100, 1000))

@dataclass()
class AudioSource:
    path: str = None
    url: str = None

@dataclass(frozen=True)
class QueuedAudio:
    name: str
    source: AudioSource
    context: discord.ext.commands.Context
    reply_to: bool = False
    disconnect_after: bool = False

@dataclass()
class AudioQueue:
    last_played: datetime
    playing_flag = False
    now_playing: QueuedAudio = None
    queue: collections.deque = field(default_factory=collections.deque)

@dataclass(frozen=True)
class Reminder:
    time: datetime
    text: str
    remindee: discord.User

print("Done importing things.")

def check_exists(path):
    if not os.path.exists(path):
        print(f"WARNING: required path {path} doesn't exist!")
        log.warn(f"Required path {path} doesn't exist!")
    return path

FART_DIRECTORY = check_exists("/home/pi/bagelbot/farts")
RL_DIRECTORY = check_exists("/home/pi/bagelbot/rl")
UNDERTALE_DIRECTORY = check_exists("/home/pi/bagelbot/ut")
STAR_WARS_DIRECTORY = check_exists("/home/pi/bagelbot/sw")
MULANEY_DIRECTORY = check_exists("/home/pi/bagelbot/jm")
CH_DIRECTORY = check_exists("/home/pi/bagelbot/ch")
SOTO_PATH = check_exists("/home/pi/bagelbot/soto.png")
SOTO_PARTY = check_exists("/home/pi/bagelbot/soto_party.mp3")
SOTO_TINY_NUKE = check_exists("/home/pi/bagelbot/tiny_soto_nuke.mp3")
WOW_PATH = check_exists("/home/pi/bagelbot/wow.mp3")
DEAN_PATH = check_exists("/home/pi/bagelbot/dean.gif")
GK_PATH = check_exists("/home/pi/bagelbot/genghis_khan.mp3")
HELLO_THERE_PATH = check_exists("/home/pi/bagelbot/sw/obi_wan_kenobi/hello_there.mp3")
SWOOSH_PATH = check_exists("/home/pi/bagelbot/sw/mace_windu/swoosh.mp3")
OHSHIT_PATH = check_exists("/home/pi/bagelbot/ohshit.mp3")
YEAH_PATH = check_exists("/home/pi/bagelbot/yeah.mp3")
GOAT_SCREAM_PATH = check_exists("/home/pi/bagelbot/the_goat_he_screams_like_a_man.mp3")
SUPER_MARIO_PATH = check_exists("/home/pi/bagelbot/super_mario_sussy.mp3")
BUG_REPORT_DIR = check_exists("/home/pi/.bagelbot/bug-reports")


async def is_wade(ctx):
    is_wade = ctx.message.author.id == 235584665564610561
    return is_wade


async def is_one_of_the_collins_or_wade(ctx):
    is_a_collin_or_wade = await is_wade(ctx) or \
        ctx.message.author.id == 188843663680339968 or \
        ctx.message.author.id == 221481539735781376
    return is_a_collin_or_wade


def wade_only():
    async def predicate(ctx):
        log.info(ctx.message.author.id)
        ret = await is_wade(ctx)
        if not ret:
            await ctx.send("Hey, only Wade can use this command.")
        return ret
    return commands.check(predicate)


def wade_or_collinses_only():
    async def predicate(ctx):
        log.info(ctx.message.author.id)
        ret = await is_one_of_the_collins_or_wade(ctx)
        if not ret:
            await ctx.send("Hey, only the Collinses (or Wade) can use this command.")
        return ret
    return commands.check(predicate)


async def update_status(bot):
    try:
        act = discord.Activity(type=discord.ActivityType.watching,
                               name=f" out, cuz you better watch out")
        await bot.change_presence(activity=act)
    except Exception:
        pass


def soundify_text(text, lang, tld):
    tts = gTTS(text=text, lang=lang, tld=tld)
    filename = tmp_fn("say", "mp3")
    tts.save(filename)
    return filename


def file_to_audio_stream(filename):
    return FFmpegPCMAudio(executable="/usr/bin/ffmpeg",
        source=filename, options="-loglevel panic")


def stream_url_to_audio_stream(url):
    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }
    return FFmpegPCMAudio(url, **FFMPEG_OPTIONS)


def youtube_to_audio_stream(url):
    log.debug(f"Converting YouTube audio: {url}")

    YDL_OPTIONS = {
        'format': 'bestvideo+bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192'
        }],
        'postprocessor_args': [
            '-ar', '16000'
        ],
        'prefer_ffmpeg': True,
        'keepvideo': False
    }

    # youtube format codes:
    # https://gist.github.com/sidneys/7095afe4da4ae58694d128b1034e01e2#youtube-video-stream-format-codes
    # https://gist.github.com/AgentOak/34d47c65b1d28829bb17c24c04a0096f
    FORMATS_IN_DECREASING_ORDER_OF_PREFERENCE = [
        # DASH audio formats
        249, # WebM     Opus    (VBR) ~50 Kbps
        250, # WebM     Opus    (VBR) ~70 Kbps
        251, # WebM     Opus    (VBR) <=160 Kbps

        140, # m4a    audio          128k
        18,  # mp4    audio/video    360p
        22,  # mp4    audio/video    720p

        # Livestream formats
        93, # MPEG-TS (HLS)    360p    AAC (LC)     128 Kbps    Yes
        91, # MPEG-TS (HLS)    144p    AAC (HE v1)  48 Kbps     Yes
        92, # MPEG-TS (HLS)    240p    AAC (HE v1)  48 Kbps     Yes
        94, # MPEG-TS (HLS)    480p    AAC (LC)     128 Kbps    Yes
        95, # MPEG-TS (HLS)    720p    AAC (LC)     256 Kbps    Yes
        96, # MPEG-TS (HLS)    1080p   AAC (LC)     256 Kbps    Yes
    ]

    extracted_info = YoutubeDL(YDL_OPTIONS).extract_info(url, download=False)
    if not extracted_info:
        print("Failed to get YouTube video info.")
        return []
    to_process = []
    if "format" not in extracted_info and "entries" in extracted_info:
        print("Looks like this is a playlist.")
        # for k, v in extracted_info.items():
        #     if k == "entries":
        #         pass
        #     print(f">>>>>>>>>> {k}={v}")
        to_process = extracted_info["entries"]
    else:
        to_process.append(extracted_info)
    print(f"Processing {len(to_process)} videos.")
    ret = []
    for info in to_process:
        formats = info["formats"]
        if not formats:
            print("Failed to get YouTube video info.")
            continue
        selected_fmt = None
        print(f"{len(formats)} formats: " + ", ".join(sorted([f["format_id"] for f in formats])))
        print(f"Preferred formats: {FORMATS_IN_DECREASING_ORDER_OF_PREFERENCE}")
        for format_id in FORMATS_IN_DECREASING_ORDER_OF_PREFERENCE:
            for fmt in formats:
                if int(fmt["format_id"]) == format_id:
                    selected_fmt = fmt
                    print(f"Found preferred format {format_id}.")
                    break
            if selected_fmt is not None:
                break
        if selected_fmt is None:
            print("Couldn't find preferred format; falling back on default.")
            selected_fmt = formats[0]
        print(f"Playing stream ID {selected_fmt['format_id']}.")
        stream_url = selected_fmt["url"]
        ret.append((info, stream_url))
    print(f"Produced {len(ret)} audio streams.")
    return ret


async def join_voice(bot, ctx, channel):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if not voice or voice.channel != channel:
        if voice:
            await voice.disconnect()
        await channel.connect()


async def ensure_voice(bot, ctx, allow_random=True):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if ctx.author.voice:
        await join_voice(bot, ctx, ctx.author.voice.channel)
        return
    options = [x for x in ctx.guild.voice_channels if len(x.voice_states) > 0]
    if not options:
        if allow_random:
            options = ctx.guild.voice_channels
        if not options:
            return
    choice = random.choice(options)
    await join_voice(bot, ctx, choice)


def stamped_fn(prefix, ext, dir="/home/pi/.bagelbot"):
    if not os.path.exists(dir):
        os.mkdir(dir)
    return f"{dir}/{prefix}-{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.{ext}"


def tmp_fn(prefix, ext):
    return stamped_fn(prefix, ext, "/tmp/bagelbot")


def download_file(url, destination):
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) " \
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    response = requests.get(url, headers=headers)
    bin = response.content
    file = open(destination, "wb")
    file.write(bin)
    file.close()


def choose_from_dir(directory, *search_key):
    log.debug(f"directory: {directory}, search: {search_key}")
    files = glob(f"{directory}/*.mp3") + glob(f"{directory}/**/*.mp3") + \
            glob(f"{directory}/*.ogg") + glob(f"{directory}/**/*.ogg")
    if not files:
        log.error(f"No files to choose from in {directory}.")
        return ""
    choice = random.choice(files)
    if search_key:
        search_key = " ".join(search_key)
        choices = process.extract(search_key, files)
        log.debug(f"options: {choices}")
        choices = [x[0] for x in choices if x[1] == choices[0][1]]
        choice = random.choice(choices)
    log.debug(f"choice: {choice}")
    return choice


def ping_host(ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.05)
        sock.connect((ip, port))
    except socket.error as e:
        return False
    return True


def fib(n):
    if n < 1:
        return 0
    if n == 1:
        return 1
    return fib(n-1) + fib(n-2)


class Debug(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.log_dumper.start()
        self.force_dump = False
        self.last_dump = None
        pass

    @tasks.loop(seconds=30)
    async def log_dumper(self):

        if not self.last_dump:
            self.last_dump = datetime.now()
            return
        now = datetime.now()

        next_dump = self.last_dump.replace( \
            hour=17, minute=0, second=0, microsecond=0)
        dump_logs_now = self.force_dump

        if dump_logs_now:
            log.info("Dumping logs off schedule by user request.")

        if now >= next_dump and self.last_dump <= next_dump:
            log.info(f"Scheduled log dump at {next_dump} triggered now.")
            dump_logs_now = True

        self.last_dump = now
        if not dump_logs_now:
            return

        man_auto = "Manual" if self.force_dump else "Automatic"
        self.force_dump = False

        if not os.path.exists(log_filename) or os.stat(log_filename).st_size == 0:
            log.info("No logs emitted in the previous period.")

        log_channel = self.bot.get_channel(908161498591928383)
        if not log_channel:
            log.warn("Failed to acquire handle to log dump channel. Retrying in 120 seconds...")
            await asyncio.sleep(120)
            log_channel = self.bot.get_channel(908161498591928383)
            if not log_channel:
                log.error("Failed to acquire handle to log dump channel!")
                return

        log.debug("Dumping.")

        discord_fn = os.path.basename(tmp_fn("LOG", "txt"))
        await log_channel.send(f"Log dump {datetime.now()} ({man_auto})",
            file=discord.File(log_filename, filename=discord_fn))

        arcfile = open(archive_filename, 'a')
        logfile = open(log_filename, 'r')
        for line in logfile.readlines():
            arcfile.write(line)
        logfile.close()
        arcfile.close()
        open(log_filename, 'w').close()

    @commands.command(help="Download the source code for this bot.")
    async def source(self, ctx):
        url = "https://github.com/jwade109/bagelbot"
        await ctx.send(url, file=discord.File(__file__))

    @commands.command(help="Manually upload logs before the next scheduled dump.")
    @wade_only()
    async def dump_logs(self, ctx):
        log.info("User requested manual log dump.")
        await ctx.send("Ok, logs will be uploaded soon.")
        self.force_dump = True

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

    @commands.command(help="Test for permissions for the nuclear codes.")
    @wade_or_collinses_only()
    async def only_collinses(self, ctx):
        await ctx.send("Tactical nuke incoming.")

    @commands.command(name="ping-endpoints", help="Test remote endpoints on the LAN.")
    async def ping_endpoints(self, ctx):
        async def do_ping(ctx, host, port):
            status = ping_host(host, port)
            if status:
                await ctx.send(f"{host}:{port} is up.")
            else:
                await ctx.send(f"{host}:{port} is down.")
        await do_ping(ctx, "bagelbox", 8000)
        await do_ping(ctx, "ancillary", 8000)

    @commands.command(help="Test for computation speed using XML RPC on remote endpoints.")
    async def fib(self, ctx):
        n = 30
        start = datetime.now()
        k = fib(n)
        end = datetime.now()
        await ctx.send(f"localhost: fib({n}) = {fib(n)}. {end - start}")
        hosts = [("bagelbox", 8000), ("ancillary", 8000)]
        for hostname, port in hosts:
            if not ping_host(hostname, port):
                log.warn(f"Not available: {hostname}:{port}")
                continue
            s = xmlrpc.client.ServerProxy(f"http://{hostname}:{port}")
            start = datetime.now()
            k = s.fib(n)
            end = datetime.now()
            await ctx.send(f"{hostname}:{port}: fib({n}) = {k}. {end - start}")

    @commands.command(name="report-bug", aliases=["bug", "bug-report"], help="Use this to report bugs with BagelBot.")
    async def report_bug(self, ctx, *description):
        msg = ctx.message
        if not description:
            await ctx.send("Please include a written description of the bug. "
                "(Attached screenshots are also a big help for debugging!)")
            return
        description = " ".join(description)
        log.debug(f"Bug report description: '{description}'.")

        ticket_name = get_bug_ticket_name()
    
        now = datetime.now()
        bug_dir = BUG_REPORT_DIR + "/" + ticket_name
        while os.path.exists(bug_dir):
            ticket_name = get_bug_ticket_name()
            bug_dir = BUG_REPORT_DIR + "/" + ticket_name
        os.mkdir(bug_dir)
        info_fn = bug_dir + "/report_info.txt"
        info_file = open(info_fn, "w")
        info_file.write(f"Description: {description}\n")
        info_file.write(f"Guild: {msg.guild}\n")
        info_file.write(f"Author: {msg.author}\n")
        info_file.write(f"Channel: {msg.channel}\n")
        info_file.write(f"Time: {now}\n")
        info_file.close()

        await ctx.send(f"Thanks for submitting a bug report. Your ticket is: {ticket_name}")

        dl_filename = None
        if msg.attachments:
            log.debug(f"Bug report directory: {bug_dir}")
            for att in msg.attachments:
                dl_filename = bug_dir + "/" + att.filename.lower()
                if any(dl_filename.endswith(image) for image in ["png", "jpeg", "gif", "jpg"]):
                    log.debug(f"Saving image attachment to {dl_filename}")
                    await att.save(dl_filename)
                else:
                    log.warn(f"Not saving attachment of unsupported type: {dl_filename}.")
                    dl_filename = None

        bug_report_channel = self.bot.get_channel(908165358488289311)
        if not bug_report_channel:
            log.error("Failed to acquire handle to bug report channel!")
            return
        discord_msg = f"```\n" + \
            f"Ticket name: {ticket_name}\n" + \
            f"Description: {description}\n" + \
            f"Guild:       {msg.guild}\n" + \
            f"Author:      {msg.author}\n" + \
            f"Channel:     {msg.channel}\n" + \
            f"Time:        {now}\n```"
        if dl_filename:
            await bug_report_channel.send(discord_msg, file=discord.File(dl_filename))
        else:
            await bug_report_channel.send(discord_msg)




class Bagels(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

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

    @commands.command(help="Check how many bagels there are.")
    async def bagels(self, ctx):
        bagels = int(get_param("num_bagels", 0))
        if bagels == 1:
            await ctx.send(f"There is 1 lonely bagel.")
        elif bagels == 69:
            await ctx.send(f"There are 69 bagels. Nice.")
        else:
            await ctx.send(f"There are {bagels} bagels.")

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


class Voice(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.now_playing = {}
        self.global_accent = get_param("global_accent", "american")
        self.accents = {
            "australian":       ("en", "com.au"),
            "british":          ("en", "co.uk"),
            "american":         ("en", "com"),
            "canadian":         ("en", "ca"),
            "indian":           ("en", "co.in"),
            "irish":            ("en", "ie"),
            "south african":    ("en", "co.za"),
            "french canadian":  ("fr", "ca"),
            "french":           ("fr", "fr"),
            "mandarin":         ("zh-CN", "com"),
            "taiwanese":        ("zh-TW", "com"),
            "brazilian":        ("pt", "com.br"),
            "portuguese":       ("pt", "pt"),
            "mexican":          ("es", "com.mx"),
            "spanish":          ("es", "es"),
            "spanish american": ("es", "com"),
            "dutch":            ("nl", "com"),
            "german":           ("de", "com")
        }
        log.debug(f"Default accent is {self.global_accent}, " \
                  f"{self.accents[self.global_accent]}")
        self.audio_driver.start()

    async def enqueue_audio(self, queued_audio):
        guild = queued_audio.context.guild
        if guild not in self.queues:
            log.debug(f"New guild audio queue: {guild}")
            self.queues[guild] = AudioQueue(datetime.now())
        log.debug(f"Enqueueing audio: guild={guild}, audio={queued_audio}")
        self.queues[guild].queue.append(queued_audio)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        log.debug(f"member={member}, before={before}, after={after}")

    @tasks.loop(seconds=2)
    async def audio_driver(self):
        try:
            for guild, audio_queue in self.queues.items():
                np = await self.get_now_playing(guild)
                if np:
                    audio_queue.now_playing = np
                    audio_queue.last_played = datetime.now()
                    print(f"{audio_queue.last_played}: {guild} is playing {np.name}.")
                else:
                    disconnect_after = False
                    if audio_queue.now_playing:
                        disconnect_after = audio_queue.now_playing.disconnect_after
                    audio_queue.now_playing = None
                    audio_queue.playing_flag = False
                    if disconnect_after:
                        voice = get(self.bot.voice_clients, guild=guild)
                        if voice:
                            await voice.disconnect()
                voice = get(self.bot.voice_clients, guild=guild)
                if voice and not audio_queue.queue and (datetime.now() - audio_queue.last_played) > timedelta(seconds=60):
                    log.info("Disconnecting after inactive period of 60 seconds.")
                    await voice.disconnect()
                    continue
                if not audio_queue.queue:
                    continue
                if voice and (voice.is_playing() or voice.is_paused()):
                    continue
                log.debug("New jobs for the audio queue.")
                to_play = audio_queue.queue.popleft()
                log.info(f"Handling queue element: guild={to_play.context.guild}, audio={to_play}")
                await ensure_voice(self.bot, to_play.context)
                voice = get(self.bot.voice_clients, guild=to_play.context.guild)
                if not voice:
                    log.error(f"Failed to connect to voice when trying to play {to_play}")
                    continue
                if to_play.reply_to:
                    await to_play.context.reply(f"Now playing: {to_play.name}", mention_author=False)
                if to_play.source.path is not None:
                    audio = file_to_audio_stream(to_play.source.path)
                elif to_play.source.url is not None:
                    audio = stream_url_to_audio_stream(to_play.source.url)
                else:
                    log.error(f"Bad audio source: {to_play}")
                    continue
                audio_queue.playing_flag = True
                voice.play(audio)
                self.now_playing[guild] = to_play

        except Exception as e:
            uhoh = f"VERY VERY BAD: Uncaught exception: {type(e)} {e}"
            print(uhoh)
            print(e.__traceback__)
            log.error(uhoh)
            log.error(e.__traceback__)

    async def get_now_playing(self, guild):
        voice = get(self.bot.voice_clients, guild=guild)
        if not voice or guild not in self.now_playing:
            return None
        # we're in voice, and there was a song playing at some point in the past.
        # see if it's still playing
        if voice.is_playing() or voice.is_paused():
            return self.now_playing[guild]
        del self.now_playing[guild]
        return None

    async def get_queue(self, ctx):
        if ctx.guild not in self.queues:
            self.queues[ctx.guild] = AudioQueue(datetime.now())
        return self.queues[ctx.guild]

    @commands.command(name="now-playing", aliases=["np"], help="What song/ridiculous Star Wars quote is this?")
    async def now_playing(self, ctx):
        np = await self.get_now_playing(ctx.guild)
        if np:
            await ctx.send(f"Playing: {np.name}")
        else:
            await ctx.send("Not currently playing anything.")

    @commands.command(aliases=["q"], help="What songs are up next?")
    async def queue(self, ctx):
        np = await self.get_now_playing(ctx.guild)
        queue = await self.get_queue(ctx)
        if not queue and not np:
            await ctx.send("Nothing currently queued. Queue up music using the `play` command.")
            return
        lines = []
        if np:
            lines.append(f"Playing     {np.name}")
        for i, audio in enumerate(queue.queue):
            line = f"{i+1:<12}{audio.name}"
            lines.append(line)
        await ctx.send("```\n===== SONG QUEUE =====\n\n" + "\n".join(lines) + "\n```")

    @commands.command(name="clear-queue", aliases=["clear", "cq"], help="Clear the song queue.")
    async def clear_queue(self, ctx):
        if ctx.guild not in self.queues or not self.queues[ctx.guild]:
            await ctx.send("Nothing currently queued!", delete_after=5)
            return
        del self.queues[ctx.guild]
        await ctx.message.add_reaction("💥")

    @commands.command(help="Skip whatever is currently playing.")
    async def skip(self, ctx):
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if not voice:
            await ctx.send("Not currently in voice!", delete_after=5)
            return
        if voice.is_playing() or voice.is_paused():
            voice.stop()
        else:
            await ctx.send("Not currently playing anything!", delete_after=5)

    @commands.command(help="Pause or unpause whatever is currently playing.")
    async def pause(self, ctx):
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if not voice:
            await ctx.send("Not currently in voice!", delete_after=5)
        elif voice.is_playing():
            await ctx.message.add_reaction("⏸️")
            voice.pause()
        elif voice.is_paused():
            await ctx.message.add_reaction("▶️")
            voice.resume()

    # @commands.command(help="I'm Mr. Worldwide.")
    # async def worldwide(self, ctx, *message):
    #     await ensure_voice(self.bot, ctx)
    #     voice = get(self.bot.voice_clients, guild=ctx.guild)
    #     if not voice:
    #         if not ctx.author.voice:
    #             await ctx.send("You're not in a voice channel!")
    #             return
    #         channel = ctx.author.voice.channel
    #         await channel.connect()
    #     voice = get(self.bot.voice_clients, guild=ctx.guild)
    #     for accent in self.accents:
    #         say = accent
    #         if message:
    #             say = " ".join(message)
    #         filename = soundify_text(say, *self.accents[accent])
    #         audio = file_to_audio_stream(filename)
    #         await self.enqueue_audio(QueuedAudio(f"Say: {say}", audio, ctx))

    @commands.command(help="Get or set the bot's accent.")
    async def accent(self, ctx, *argv):
        if not argv:
            await ctx.send(f"My current accent is \"{self.global_accent}\".")
            return
        arg = " ".join(argv).lower()
        available = ", ".join([x for x in self.accents])
        if arg == "help":
            await ctx.send("Set my accent using \"bb accent <accent>\". " \
                f"Available accents are: {available}")
            return
        if arg not in available:
            await ctx.send("Sorry, that's not a valid accent. " \
                f"Available accents are: {available}")
            return
        self.global_accent = arg
        set_param("global_accent", arg)
        await ctx.send(f"Set accent to \"{arg}\".")

    @commands.command(help="Leave voice chat.")
    async def leave(self, ctx):
        if not ctx.voice_client:
            await ctx.send("Not connected to voice!")
            return
        await ctx.voice_client.disconnect()

    @commands.command(help="Join voice chat.")
    async def join(self, ctx):
        if random.random() < 0.023:
            await self.generic_sound_effect_callback(ctx, SWOOSH_PATH)
        else:
            await self.generic_sound_effect_callback(ctx, HELLO_THERE_PATH)

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
        say = " ".join(message)
        filename = soundify_text(say, *self.accents[self.global_accent])
        source = AudioSource()
        source.path = filename
        await self.enqueue_audio(QueuedAudio(f"Say: {say}", source, ctx))

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
        filename = soundify_text(" ".join(message), *self.accents[self.global_accent])
        source = AudioSource()
        source.path = filename
        qa = QueuedAudio(filename, source, ctx, False, True)
        await self.enqueue_audio(qa)
        # await asyncio.sleep(3)
        # while await self.get_now_playing(ctx.guild):
        #     await asyncio.sleep(0.2)
        #     print("Waiting to finish...")
        # await voice.disconnect()

    async def generic_sound_effect_callback(self, ctx, filename):
        await ensure_voice(self.bot, ctx)
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if not voice:
            if not ctx.author.voice:
                await ctx.send("You're not in a voice channel!")
                return
            channel = ctx.author.voice.channel
            await channel.connect()
        source = AudioSource()
        source.path = filename
        await self.enqueue_audio(QueuedAudio(f"{filename} (effect)", source, ctx))

    @commands.command(name="genghis-khan", aliases=["gk", "genghis", "khan"],
        help="Something something a little bit Genghis Khan.")
    async def kahn(self, ctx):
        await self.generic_sound_effect_callback(ctx, GK_PATH)

    @commands.command(name="rocket-league", aliases=["rl"], help="THIS IS ROCKET LEAGUE!")
    async def rocket_league(self, ctx, *search):
        choice = choose_from_dir(RL_DIRECTORY, *search)
        await self.generic_sound_effect_callback(ctx, choice)

    @commands.command(aliases=["ut"], help="The music... it fills you with determination.")
    async def undertale(self, ctx, *search):
        choice = choose_from_dir(UNDERTALE_DIRECTORY, *search)
        await self.generic_sound_effect_callback(ctx, choice)

    @commands.command(aliases=["sw"], help="This is where the fun begins.")
    async def starwars(self, ctx, *search):
        choice = choose_from_dir(STAR_WARS_DIRECTORY, *search)
        await self.generic_sound_effect_callback(ctx, choice)

    @commands.command(aliases=["jm"], help="I don't look older, I just look worse.")
    async def mulaney(self, ctx, *search):
        choice = choose_from_dir(MULANEY_DIRECTORY, *search)
        await self.generic_sound_effect_callback(ctx, choice)

    @commands.command(help="JUUUAAAAAAANNNNNNNNNNNNNNNNNNNNNNNNNN SOTOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO")
    async def soto(self, ctx):
        await ctx.send(file=discord.File(SOTO_PATH))
        await self.generic_sound_effect_callback(ctx, SOTO_PARTY)

    @commands.command(aliases=["death", "nuke"], help="You need help.")
    @wade_or_collinses_only()
    async def surprise(self, ctx):
        await self.generic_sound_effect_callback(ctx, SOTO_TINY_NUKE)
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        await asyncio.sleep(3)
        while await self.get_now_playing(ctx.guild):
            await asyncio.sleep(0.2)
            print("Waiting to finish...")
        await voice.disconnect()

    @commands.command(help="GET MOBIUS HIS JET SKI")
    async def wow(self, ctx):
        await self.generic_sound_effect_callback(ctx, WOW_PATH)
        
    @commands.command(help="Oh shoot.")
    async def ohshit(self, ctx):
        await self.generic_sound_effect_callback(ctx, OHSHIT_PATH)
        
    @commands.command(help="Yeah.")
    async def yeah(self, ctx):
        await self.generic_sound_effect_callback(ctx, YEAH_PATH)
        
    @commands.command(help="He screams like a man.")
    async def goat(self, ctx):
        await self.generic_sound_effect_callback(ctx, GOAT_SCREAM_PATH)
        
    @commands.command(help="Itsa me!")
    async def mario(self, ctx):
        await self.generic_sound_effect_callback(ctx, SUPER_MARIO_PATH)

    @commands.command(aliases=["youtube", "yt"], help="Play a YouTube video, maybe.")
    async def play(self, ctx, url):
        await ctx.message.add_reaction("👍")
        log.debug(f"Playing YouTube audio: {url}")
        results = youtube_to_audio_stream(url)
        if not results:
            await ctx.send("Failed to convert that link to something playable. Sorry about that.")
            return
        for info, stream_url in results:
            title = info["title"]
            # for k, v in info.items():
            #     print(f"======= {k}\n{v}")
            source = AudioSource()
            source.url = stream_url
            await self.enqueue_audio(QueuedAudio(f"{title} (<{info['webpage_url']}>)", source, ctx, True))


class Miscellaneous(commands.Cog): 

    @commands.command(name="even-odd", help="Check if a number is even or odd.")
    async def even_odd(self, ctx, num: int):
        r = requests.get(f"https://api.isevenapi.xyz/api/iseven/{num}/")
        d = r.json()
        ad = d["ad"]
        iseven = d["iseven"]
        if iseven:
            await ctx.send(f"{num} is even.")
        else:
            await ctx.send(f"{num} is odd.")
        await ctx.send("<<< " + ad + " >>>")

    @commands.command(help="Get the definition of a word.")
    async def define(self, ctx, word: str):
        log.debug(f"{ctx.message.author} wants the definition of '{word}'.")
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
        await ctx.send(file=discord.File(DEAN_PATH))

    @commands.command(help="Ask wikipedia for things.")
    async def wikipedia(self, ctx, query: str):
        await ctx.send(wiki.summary(query))

    @commands.command(help="Get info about a pokemon by its name.", category="pokemon")
    async def pokedex(self, ctx, id: int = None):
        if id is None:
            id = random.randint(1, 898)
        if id > 898:
            await ctx.send("There are only 898 pokemon.")
            return
        if id < 1:
            await ctx.send("Only takes numbers greater than zero.")
            return
        try:
            p = pypokedex.get(dex=id)
        except:
            await ctx.send(f"Pokemon `{name}` was not found.")
            return
        embed = discord.Embed()
        embed.title = p.name.capitalize()
        embed.description = f"{p.name.capitalize()} ({p.dex}). " \
            f"{', '.join([x.capitalize() for x in p.types])} type. " \
            f"{p.weight/10} kg. {p.height/10} m."
        embed.set_image(url=f"https://assets.pokemon.com/assets/cms2/img/pokedex/detail/{str(id).zfill(3)}.png")
        await ctx.send(embed=embed)

    @commands.command(help="Get info about a pokemon by Pokedex ID.", category="pokemon")
    async def pokemon(self, ctx, name: str = None):
        if not name:
            await self.pokedex(ctx, None)
            return
        try:
            p = pypokedex.get(name=name)
        except:
            await ctx.send(f"Pokemon `{name}` was not found.")
            return
        await self.pokedex(ctx, p.dex)

    @commands.command(help="Drop some hot Bill Watterson knowledge.")
    async def ch(self, ctx):
        files = [os.path.join(path, filename)
                 for path, dirs, files in os.walk(CH_DIRECTORY)
                 for filename in files
                 if filename.endswith(".gif")]
        choice = random.choice(files)
        result = re.search(r".+(\d{4})(\d{2})(\d{2}).gif", choice)
        year = int(result.group(1))
        month = int(result.group(2))
        day = int(result.group(3))
        message = f"{calendar.month_name[month]} {day}, {year}."
        await ctx.send(message, file=discord.File(choice))

    @commands.command(help="A webcomic of romance, sarcasm, math, and language.")
    async def xkcd(self, ctx, num: int = None):
        path = "" if num is None else str(num)
        r = requests.get(f"https://xkcd.com/{path}/info.0.json")
        data = r.json()
        print(data)
        embed = discord.Embed()
        embed.title = data["title"]
        embed.set_image(url=data["img"])
        await ctx.send(embed=embed)

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
        self.location = request_location()
        # self.video_in_the_morning.start()
        self.sunrise_capture.start()
        self.last_dt_to_sunrise = None

        srtime = get_sunrise_today(*self.location)
        log.debug(f"For reference, sunrise time today is {srtime}.")

    @tasks.loop(minutes=2)
    async def sunrise_capture(self):
        srtime = get_sunrise_today(*self.location)
        now = datetime.now()
        dt_to_sunrise = srtime - now
        if self.last_dt_to_sunrise and dt_to_sunrise < timedelta() and self.last_dt_to_sunrise >= timedelta():
            log.info(f"Sunrise reported as {srtime}, which is roughly now.")
            filename = stamped_fn("sunrise", "jpg")
            self.take_still(filename)
        self.last_dt_to_sunrise = dt_to_sunrise

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
        await ctx.send(f"Recording for {seconds} secods.")
        filename = stamped_fn("cap", "h264")
        await self.take_video(filename, seconds)
        await ctx.send("Done.")
        file_size = os.path.getsize(filename)
        limit = 8 * 1024 * 1024
        if file_size < limit:
            await ctx.send(file=discord.File(filename))
        else:
            await ctx.send("Video is too large for message embed. It can be " \
                "transferred from the Raspberry Pi (by someone on the LAN) " \
                f"using this command: `scp pi@10.0.0.137:{filename} .`")

    @commands.command(help="Get some wisdom from the deep.")
    async def wisdom(self, ctx):
        w = get_wisdom()
        log.debug(w)
        await ctx.send(w)

    @commands.command(help="Get some bacon.")
    async def bacon(self, ctx):
        b = get_bacon()
        log.debug(b)
        await ctx.send(b)

    # @commands.command(name="timelapse-start", help="Start timelapse.")n
    async def timelapse_start(self, ctx):
        log.debug("Enabling timelapse capture.")
        self.timelapse_active = True
        await ctx.send("timelapse_active = True")

    # @commands.command(name="timelapse-stop", help="Stop timelapse.")
    async def timelapse_stop(self, ctx):
        log.debug("Disabling timelapse capture.")
        self.timelapse_active = False
        await ctx.send("timelapse_active = False")

    @commands.command(aliases=["day"], help="See the latest pictures of sunrise.")
    async def sunrise(self, ctx, *options):
        log.debug(f"Mmmm, {ctx.message.author} wants it to be day. (opts={options})")
        files = glob(f"/home/pi/.bagelbot/sunrise*.jpg")
        if not files:
            await ctx.send("Sorry, I don't have any pictures of sunrise to show you.")
            return
        choice = random.choice(files)
        if "today" in options or "latest" in options:
            files = sorted(files)
            choice = files[-1]
        log.info(f"File of choice: {choice}")
        result = re.search("sunrise-(.*).jpg", os.path.basename(choice))
        stamp = datetime.strptime(result.groups(1)[0], "%Y-%m-%dT%H-%M-%S")
        stamp.strftime('%I:%M %p on %B %d, %Y')
        await ctx.send(stamp.strftime('%I:%M %p on %B %d, %Y'), file=discord.File(choice))


def realign_tense_of_task(user_provided_task):
    ret = user_provided_task.replace("my", "your").replace("My", "your")
    ret = user_provided_task.replace("me", "you").replace("Me", "You")
    if ret.startswith("to "):
        ret = ret[3:]
    return ret


def reminder_msg(mention, thing_to_do, date, is_channel):
    tstr = f"**{realign_tense_of_task(thing_to_do)}**"
    dstr = f"**{date.strftime('%I:%M %p on %B %d, %Y')}**"
    at_here = "@here " if is_channel else ""
    choices = [
        f"{at_here}Hey {mention}, You asked me to remind you to {tstr} at {dstr}, which is right about now.",
        f"{at_here}Hey {mention}, you wanted me to remind you to {tstr} right now.",
        f"{at_here}Yo, {mention}, it's time for you to do {tstr}, since the current time is {dstr}.",
        # f"{dstr} is the time of right now, and {tstr} is the thing to be done right now.",
        f"{at_here}Hey, {mention}, don't forget about your {tstr}, which is to be done at {dstr} (right now).",
        f"{at_here}Attention {mention}: I will be disappointed in you if you don't {tstr} immediately.",
        f"{at_here}HEY {mention}, IT'S TIME FOR {tstr} BECAUSE IT IS {dstr} WHICH IS RIGHT NOW AND YOU TOLD ME TO TELL YOU WHEN IT WAS RIGHT NOW AND IT IS RIGHT NOW SO PLEASE IMMEDIATELY COMMENCE DOING {tstr} THANKS."
    ]
    return random.choice(choices)


class Chess(commands.Cog):

    def __init__(self):
        pass

    def write_board(self, board):
        set_param("chess_state", board.fen())

    def load_board(self):
        chess_state = get_param("chess_state", None)
        if not chess_state:
            board = chess.Board()
            self.write_board(board)
        else:
            board = chess.Board(chess_state)
        return board

    @commands.command()
    async def chess_move(self, ctx, move: str):
        board = self.load_board()
        board.push_san(move)
        self.write_board(board)
        await self.chess_show(ctx)

    @commands.command()
    async def chess_show(self, ctx):
        board = self.load_board()
        svg = chess.svg.board(board)
        fn = tmp_fn("chess", "png")
        log.debug(f"Rendering chess state to {fn}.")
        svg2png(bytestring=svg, write_to=fn)
        color = "White" if board.turn else "Black"
        await ctx.send(f"{color} to play.", file=discord.File(fn))


class Productivity(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.reminders = get_param("reminders", [])
        self.process_reminders.start()
        self.todos = get_param("todo_lists", {})

    def get_todos(self, id):
        if id not in self.todos:
            self.todos[id] = []
        return self.todos[id]
        
    def set_todos(self, id, todos):
        self.todos[id] = todos
        set_param("todo_lists", self.todos)

    def add(self, id, todo : str):
        todos = self.get_todos(id)
        todos.append(todo)
        self.set_todos(id, todos)

    def delete(self, id, index):
        print("Delete element {index}.")

    @commands.command(aliases=["cl", "captains-log"], help="Look your to-do list, or add a new to-do item.")
    async def todo(self, ctx, *varargs):
        id = ctx.message.author.id

        if not varargs:
            varargs = ["show"]
        subcommand = varargs[0]

        if subcommand == "show":
            varargs = varargs[1:]
            todos = self.get_todos(id)
            if not todos:
                await ctx.send("You have no items on your to-do list. To add an item, " \
                    "use `bb todo add [thing you need to do]`.")
                return
            username = ctx.message.author.name.upper()
            resp = f"```\n=== {username}'S TODO LIST ==="
            for i, todo in enumerate(todos):
                resp += f"\n{i+1:<5} {todo}"
            resp += "\n```"
            await ctx.send(resp)
            return
        if subcommand == "add":
            varargs = varargs[1:]
            if not varargs:
                await ctx.send("I can't add nothing to your to-do list!")
                return
            task = " ".join(varargs)
            self.add(id, task)
            await ctx.send(f"Ok, I've added \"{task}\" to your to-do list.")
            return
        if subcommand == "del" or subcommand == "done":
            varargs = varargs[1:]
            index = None
            try:
                index = int(varargs[0])
            except Exception:
                await ctx.send("This command requires a to-do item number to delete.")
                return
            todos = self.get_todos(id)
            if index > len(todos) or index < 1:
                await ctx.send(f"Sorry, I can't delete to-do item {index}.")
                return
            del todos[index-1]
            self.set_todos(id, todos)
            await ctx.send(f"Ok, I've removed item number {index} from your to-do list.")
            return
        else:
            if not varargs:
                await ctx.send("I can't add nothing to your to-do list!")
                return
            task = " ".join(varargs)
            self.add(id, task)
            await ctx.send(f"Ok, I've added \"{task}\" to your to-do list.")
            return

        await ctx.send(f"`{subcommand}`` is not a valid todo command. Valid subcommands are: `show`, `add`, `del`.")

    @commands.command(aliases=["remindme"], help="Slip into ya dms.")
    async def remind(self, ctx, channel_or_user: Union[discord.TextChannel, discord.Member, None], *unstructured_garbage):

        am = discord.AllowedMentions(users=False)

        requested_by = ctx.message.author.id
        user_to_remind, channel_id = ctx.message.author.id, None

        if channel_or_user:
            if isinstance(channel_or_user, discord.abc.GuildChannel):
                channel_id = channel_or_user.id
                user_to_remind = None
            elif isinstance(channel_or_user, discord.abc.User):
                user_to_remind = channel_or_user.id
            else:
                log.error(f"Unsupported type: {type(channel_or_user)}")

        log.debug(f"{channel_or_user}: user={user_to_remind}, channel={channel_id}")

        if user_to_remind and user_to_remind == self.bot.user.id:
            await ctx.send("I'm a computer, dummy. I never forget.")
            return

        arg = " ".join(unstructured_garbage)
        if arg.startswith("me "):
            arg = arg[3:]
        pattern = r"(.+)\s(\bat\b\s.+|\bby\b\s.+|\bon\b\s.+|\bin\b\s.+)"
        matches = re.search(pattern, arg)
        if not matches:
            log.debug(f"Request didn't match regex pattern: {arg}")
            await ctx.send("Sorry, I couldn't understand that. " \
                "Please phrase your remindme request like this:\n" \
                "```bb remindme to do the dishes by tomorrow```" \
                "```bb remindme to do my homework in 4 days```"
                "```bb remindme view the quadrantids meteor shower on January 2, 2022, 1 am```"
                "```bb remindme eat a krabby patty at 3 am```")
            return
        thing_to_do = matches.group(1)
        datestr = matches.group(2)
        date = parse(datestr)
        if not date:
            await ctx.send("Sorry, I couldn't understand that. " \
                "Please phrase your remindme request like this:\n" \
                "```bb remindme [thing to do] [when to do it]```" \
                "```bb remindme to do the dishes by tomorrow```" \
                "```bb remindme to do my homework in 4 days```"
                "```bb remindme view the quadrantids meteor shower on January 2, 2022, 1 am```"
                "```bb remindme eat a krabby patty at 3 am```")
            return

        noun = "you"
        if channel_or_user:
            noun = channel_or_user.mention

        log.debug(f"thing={thing_to_do}, datestr={datestr}, date={date}")
        msg = await ctx.send(f"You want me to remind {noun} to **{realign_tense_of_task(thing_to_do)}** " \
            f"at **{date.strftime('%I:%M %p on %B %d, %Y')}**. Is this correct?", allowed_mentions=am)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        def check(reaction, user):
            return reaction.message == msg and user == ctx.message.author and \
                str(reaction.emoji) in ["✅", "❌"]

        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=30)
        except asyncio.TimeoutError:
            log.debug("Waiting for reaction timed out.")
            await msg.edit(content=f"Ok, I won't remind {noun} to " \
                f"**{realign_tense_of_task(thing_to_do)}** " \
                f"at **{date.strftime('%I:%M %p on %B %d, %Y')}**.", allowed_mentions=am)
            await msg.remove_reaction("✅", self.bot.user)
            await msg.remove_reaction("❌", self.bot.user)
            return

        await msg.remove_reaction("✅", self.bot.user)
        await msg.remove_reaction("❌", self.bot.user)
        # await msg.remove_reaction(reaction.emoji, ctx.message.author)

        success = str(reaction.emoji) == "✅"
        if not success:
            await msg.edit(content=f"Ok, I won't remind {noun} to " \
                f"**{realign_tense_of_task(thing_to_do)}**.", allowed_mentions=am)
            return

        if date < datetime.now():
            await msg.edit(content=f"Sorry, I can't remind {noun} to " \
                f"**{realign_tense_of_task(thing_to_do)}** " \
                f"at **{date.strftime('%I:%M %p on %B %d, %Y')}**, " \
                "since the specified time is in the past.", allowed_mentions=am)
            return

        await msg.edit(content=f"Gotcha, I'll remind {noun} to " \
            f"**{realign_tense_of_task(thing_to_do)}** " \
            f"at **{date.strftime('%I:%M %p on %B %d, %Y')}**.", allowed_mentions=am)

        reminder = {"thing": thing_to_do, "datetime": date,
            "user": user_to_remind, "channel": channel_id, "requested_by": requested_by}
        reminder_database = get_param("reminders", [])
        reminder_database.append(reminder)
        set_param("reminders", reminder_database)
        self.reminders = reminder_database

    @tasks.loop(seconds=10)
    async def process_reminders(self):
        am = discord.AllowedMentions(users=False)
        write_to_disk = False
        for rem in self.reminders:
            date = rem["datetime"]
            thing_to_do = rem["thing"]
            if date <= datetime.now():
                if rem["user"]:
                    is_channel = False
                    handle = await self.bot.fetch_user(rem["user"])
                else:
                    handle = await self.bot.fetch_channel(rem["channel"])
                    is_channel = True
                rem["complete"] = True
                write_to_disk = True
                log.info(f"Reminding {handle}: {thing_to_do}")
                await handle.send(reminder_msg(handle.mention, \
                    thing_to_do, date, is_channel), allowed_mentions=am)
        self.reminders = [x for x in self.reminders if "complete" not in x]
        if write_to_disk:
            set_param("reminders", self.reminders)

    @commands.command(name="show-reminders", aliases=["sr"], help="Show your pending reminders.")
    async def show_reminders(self, ctx):
        am = discord.AllowedMentions(users=False)
        to_send = "```\n" + ctx.message.author.name + "'s Reminders:\n"

        async def rem2str(rem):
            channel_or_user = None
            requested_by = await self.bot.fetch_user(rem["requested_by"])
            if not rem["channel"]:
                channel_or_user = await self.bot.fetch_user(rem["user"])
            else:
                channel_or_user = await self.bot.fetch_channel(rem["channel"])
            date = rem["datetime"]
            thing = rem["thing"]
            postamble = ""
            if requested_by.id != ctx.message.author.id:
                postamble = f" (reminded by {requested_by.name})"
            elif channel_or_user.id != ctx.message.author.id:
                if rem["channel"]:
                    postamble = f" (reminding #{channel_or_user.name})"
                else:
                    postamble = f" (reminding {channel_or_user.name})"
            return f"{date.strftime('%I:%M %p on %B %d, %Y')}: {thing}{postamble}."
        
        i = 0
        for rem in sorted(self.reminders, key=lambda x: x["datetime"]):
            if rem["requested_by"] == ctx.message.author.id or \
               rem["channel"] is None and rem["user"] == ctx.message.author.id:
                i += 1
                to_send += f"({i}) " + await rem2str(rem) + "\n"

        to_send += "```"

        if not i:
            await ctx.send("You have no pending reminders.")
            return

        await ctx.send(to_send, allowed_mentions=am)

    @commands.command(help="Slip into ya dms.")
    async def dm(self, ctx, user: discord.User, *message):
        message = " ".join(message)
        if not message:
            message = random.choice(["Hey, bitch.",
                "Sup, bitch.", "Bitch.", "Yo, bitch.", "Big."])
        log.debug(message)
        await user.send(message)

    # @commands.command(aliases=["remindme"], help="Ask Bagelbot to remind you of something.")
    # async def remind(self, ctx, *varags):

def main():

    STILL_RES = (3280, 2464)
    VIDEO_RES = (1080, 720)
    pi_camera = picamera.PiCamera()
    bagelbot = commands.Bot(command_prefix=["$ ", "Bb ", "bb ", "BB "], case_insensitive=True)

    @bagelbot.event
    async def on_ready():
        print("Connected.")
        log.info("Connected.")
        await update_status(bagelbot)

    @bagelbot.event
    async def on_disconnect():
        pass
        # print("Disconnected.")
        # log.info("Disconnected.")

    @bagelbot.event
    async def on_resume():
        pass
        # print("Resumed.")
        # log.info("Resumed.")

    @bagelbot.event
    async def on_command_error(ctx, e):
        if type(e) is discord.ext.commands.errors.CommandNotFound:
            await ctx.send("That isn't a recognized command.")
            return
        errstr = format_exception(type(e), e, e.__traceback__)
        errstr = "\n".join(errstr)
        s = f"Error: {type(e).__name__}: {e}\n{errstr}\n"
        await ctx.send(f"Error: {type(e).__name__}")
        log.error(f"{ctx.message.content}:\n{s}")
        
        bug_report_channel = bagelbot.get_channel(908165358488289311)
        if not bug_report_channel:
            log.error("Failed to acquire handle to bug report channel!")
            return
        msg = ctx.message
        await bug_report_channel.send(f"```\n{msg.guild} {msg.channel} {msg.author} {msg.content}:\n{s}\n```")

    @bagelbot.event
    async def on_command(ctx):
        msg = ctx.message
        log.debug(f"{msg.guild} {msg.channel} {msg.author} {msg.content}")

    @bagelbot.event
    async def on_message(message):
        if message.author == bagelbot.user:
            return
        words = message.content.strip().split()
        cleaned = message.content.strip().lower()

        haiku = detect_haiku(cleaned)
        words = [x.lower() for x in words if len(x) > 9 and x[0].lower() != 'b' and x.isalpha()]
        if haiku:
            log.info(f"Message {cleaned} is a haiku: {haiku}")
            await message.channel.send(f"...\n*{haiku[0]}*\n*{haiku[1]}*\n*{haiku[2]}*\n" + \
                f"- {message.author.name}")
        elif "too hot" in cleaned:
            await message.channel.send("*𝅗𝅥 Hot damn 𝅘𝅥*")
        elif words and random.random() < 0.03:
            selection = random.choice(words)
            print(selection)
            if selection.startswith("<@"): # discord user mention
                print(f"'{selection}' is a user mention or emoji.")
            elif validators.url(selection):
                print(f"'{selection}' is a URL.")
            else:
                if selection[0] in ['a', 'e', 'i', 'o', 'u', 'l', 'r']:
                    make_b = "B" + selection
                else:
                    make_b = "B" + selection[1:]
                if make_b[-1] is not ".":
                    make_b = make_b + "."
                print(make_b)
                await message.channel.send(make_b)
        elif random.random() < 0.002:
            w = get_wisdom()
            log.debug(f"Sending unsolicited wisdom to {message.author}: {w}")
            await message.channel.send(w)
        # maybe_quote = get_quote(message.content.strip())
        # if maybe_quote:
        #     await message.channel.send(maybe_quote)
        birthday_dialects = ["birth", "burf", "smeef", "smurf"]
        to_mention = message.author.mention
        if message.mentions:
            to_mention = message.mentions[0].mention
        for dialect in birthday_dialects:
            if dialect in cleaned:
                await message.channel.send(f"Happy {dialect}day, {to_mention}!")
                break
        await bagelbot.process_commands(message)

    bagelbot.add_cog(Debug(bagelbot))
    bagelbot.add_cog(Bagels(bagelbot))
    bagelbot.add_cog(Voice(bagelbot))
    bagelbot.add_cog(Camera(bagelbot, pi_camera, STILL_RES, VIDEO_RES))
    bagelbot.add_cog(Miscellaneous())
    bagelbot.add_cog(Productivity(bagelbot))
    bagelbot.add_cog(Farkle(bagelbot))
    bagelbot.run(get_param("DISCORD_TOKEN"))



if __name__ == "__main__":
    main()

