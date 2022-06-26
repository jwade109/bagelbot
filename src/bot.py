#! /usr/bin/env python3

print("Starting bagelbot...")

import os
import sys
import logging
from ws_dir import WORKSPACE_DIRECTORY

# writing daily logfile to log.txt;
# will append this file periodically to archive.txt,
# as well as dump it to the internal logging channel

# any calls to log.debug, log.info, etc. will be
# written to the daily logfile, and eventually will
# be dumped to the development server. standard
# print() calls will not be recorded in this way

log_filename = WORKSPACE_DIRECTORY + "/log.txt"
archive_filename = WORKSPACE_DIRECTORY + "/private/archive.txt"
logging.basicConfig(filename=log_filename,
    level=logging.WARN, format="%(levelname)-8s %(asctime)s.%(msecs)03d %(name)-16s %(funcName)-40s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("bagelbot")
log.setLevel(logging.DEBUG)

log.info("STARTING. =============================")
log.info(f"Program args: {sys.argv}")
log.info(f"CWD: {os.getcwd()}")
log.info(f"Workspace directory: {WORKSPACE_DIRECTORY}")
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
from dateparser import parse as dparse
import itertools
from bs4 import BeautifulSoup # for bacon
from functools import lru_cache # for SW EP3 quote cache
from subprocess import Popen # for automatic git commit

try: # just don't enable camera when not available
    import picamera
except Exception:
    print("\n <<< WARNING: Running without picamera! >>>\n\n")
    picamera = None

# for sunrise and sunset timings
import suntime

# for getting boot time
import psutil
import time

from farkle import Farkle
from gritty import do_gritty

from state_machine import get_param, set_param
import giphy as giphy
from haiku import detect_haiku
from ssh_sessions import ssh_sessions
from thickofit import prompt_module_response as singalong
from remindme import RemindV2
from othello import Othello

# get the datetime of today's sunrise; will return a time in the past if after sunrise
def get_sunrise_today(lat, lon):
    sun = suntime.Sun(lat, lon)
    now = datetime.now()
    return sun.get_local_sunrise_time(now).replace(tzinfo=None)

# get a rough estimate of where the host computer is located
def request_location(on_failure=[37, -81]):
    try:
        log.info("Requesting location from remote...")
        response = requests.get("http://ipinfo.io/json")
        data = response.json()
        loc = [float(x) for x in data['loc'].split(",")]
        log.info(f"Got {loc}.")
    except Exception as e:
        log.error(f"Failed to get location: {type(e)}, {e}")
        return on_failure
    return loc

# get a bunch of text from this very silly web API
def get_bacon():
    html = requests.get(f"https://baconipsum.com/?paras={random.randint(1,5)}" \
        "&type=meat-and-filler&start-with-lorem=0").content
    soup = BeautifulSoup(html, 'html.parser')
    ret = soup.find("div", {"class": "anyipsum-output"}).get_text()
    if len(ret) > 1800:
        ret = ret[:1800]
    return ret

# get a bunch of text from this very silly web API
def get_wisdom():
    html = requests.get(f"https://fungenerators.com/random/sentence").content
    soup = BeautifulSoup(html, 'html.parser')
    ret = soup.find("h2").get_text()
    if len(ret) > 1800:
        ret = ret[:1800]
    return ret

# generates a memorable-yet-random bug ticket name, something like electron-pug-892
def get_bug_ticket_name():
    return randomname.get_name(adj=('physics'), noun=('dogs')) + \
        "-" + str(random.randint(100, 1000))

# clears all emoji from a message if possible; if not, clears all emojis we own
async def clear_as_many_emojis_as_possible(msg):
    try:
        await msg.clear_reactions()
    except:
        msg = await msg.channel.fetch_message(msg.id)
        for reaction in msg.reactions:
            if not reaction.me:
                continue
            async for user in reaction.users():
                try:
                    await reaction.remove(user)
                except Exception:
                    pass

# adds emojis to the given message and and gives the user a certain period of
# time to react with them. returns immediately if the user reacts (and returns
# the reaction they used), or will return None if the timeout is reached before
# the user responds
async def prompt_user_to_react_on_message(bot, msg, target_user, emojis, timeout):

    log.debug(f"Prompting reaction: m={msg.content}, u={target_user}, e={emojis}, t={timeout}")

    for emoji in emojis:
        await msg.add_reaction(emoji)

    def check(reaction, user):
        if user == bot.user:
            return False
        if target_user is None:
            return reaction.message == msg and str(reaction.emoji) in emojis
        return reaction.message == msg and user == target_user and \
            str(reaction.emoji) in emojis
    try:
        reaction, user = await bot.wait_for("reaction_add", check=check, timeout=timeout)
    except asyncio.TimeoutError:
        log.debug("Waiting for reaction timed out.")
        return None
    log.debug(f"Got reaction from {user}: {reaction}")
    return reaction

# converts a timedelta to a plain english string
def strftimedelta(td):
    seconds = int(td.total_seconds())
    periods = [
        ('year',        60*60*24*365),
        ('month',       60*60*24*30),
        ('day',         60*60*24),
        ('hour',        60*60),
        ('minute',      60),
        ('second',      1)
    ]
    strings=[]
    for period_name, period_seconds in periods:
        if seconds > period_seconds:
            period_value , seconds = divmod(seconds, period_seconds)
            has_s = 's' if period_value > 1 else ''
            strings.append("%s %s%s" % (period_value, period_name, has_s))
    return ", ".join(strings)

# struct for audio source; support for audio stored on the filesystem (path)
# or network-streamed audio (url). only one should be populated
@dataclass()
class AudioSource:
    path: str = None
    url: str = None

# struct for audio queue element; audio plus context information for
# informing the user about the status of the request
@dataclass(frozen=True)
class QueuedAudio:
    name: str
    pretty_url: str
    source: AudioSource
    context: discord.ext.commands.Context
    reply_to: bool = False
    disconnect_after: bool = False

# audio queue struct; on a per-server basis, represents an execution
# state for playing audio and enqueueing audio requests
@dataclass()
class AudioQueue:
    last_played: datetime
    playing_flag = False
    now_playing: QueuedAudio = None
    queue: collections.deque = field(default_factory=collections.deque)

print("Done importing things.")

# this entire block below is for populating a LOT of resource paths,
# and making it very obvious if (due to negligence, malfeasance, etc)
# the path does not exist, because that's bad
def check_exists(path):
    if not os.path.exists(path):
        print(f"WARNING: required path {path} doesn't exist!")
        log.warning(f"Required path {path} doesn't exist!")
    return path

# begin filesystem resources
# using absolute filepaths so this can be run via a chron job
FART_DIRECTORY = check_exists(WORKSPACE_DIRECTORY + "/media/farts")
RL_DIRECTORY = check_exists(WORKSPACE_DIRECTORY + "/media/rl")
UNDERTALE_DIRECTORY = check_exists(WORKSPACE_DIRECTORY + "/media/ut")
STAR_WARS_DIRECTORY = check_exists(WORKSPACE_DIRECTORY + "/media/sw")
MULANEY_DIRECTORY = check_exists(WORKSPACE_DIRECTORY + "/media/jm")
CH_DIRECTORY = check_exists(WORKSPACE_DIRECTORY + "/media/ch")
SOTO_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/images/soto.png")
SOTO_PARTY = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/soto_party.mp3")
SOTO_TINY_NUKE = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/tiny_soto_nuke.mp3")
WOW_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/wow.mp3")
GK_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/genghis_khan.mp3")
HELLO_THERE_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sw/obi_wan_kenobi/hello_there.mp3")
SWOOSH_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sw/mace_windu/swoosh.mp3")
OHSHIT_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/ohshit.mp3")
YEAH_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/yeah.mp3")
GOAT_SCREAM_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/goat.mp3")
SUPER_MARIO_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/super_mario_sussy.mp3")
BUHH_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/buhh.mp3")
DUMB_FISH_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/images/dumb_fish.png")
DOG_PICS_DIR = check_exists(WORKSPACE_DIRECTORY + "/private/dog_pics") # in home dir for privacy -- maybe being paranoid
WII_EFFECTS_DIR = check_exists(WORKSPACE_DIRECTORY + "/media/wii")
PICTURE_OF_BAGELS = check_exists(WORKSPACE_DIRECTORY + "/media/images/bagels.jpg")
BUG_REPORT_DIR = check_exists(WORKSPACE_DIRECTORY + "/bug-reports")
GENERATED_FILES_DIR = check_exists(WORKSPACE_DIRECTORY + "/generated")
# end filesystem resources

# is it a security hazard to put the full file paths in source control?
# the world may never know

# returns a reference to the internal logging channel,
# where log files are dumped periodically
def get_log_channel(bot):
    return bot.get_channel(908161498591928383)

# assertion that the command caller is the creator of this bot;
# used to prevent rubes from invoking powerful commands
async def is_wade(ctx):
    is_wade = ctx.message.author.id == 235584665564610561
    return is_wade

# assertion which allows only Collin Smith, Collin Deans, or Wade
# to run this command
async def is_one_of_the_collins_or_wade(ctx):
    is_a_collin_or_wade = await is_wade(ctx) or \
        ctx.message.author.id == 188843663680339968 or \
        ctx.message.author.id == 221481539735781376
    return is_a_collin_or_wade

# decorator for restricting a command to wade
def wade_only():
    async def predicate(ctx):
        # log.info(ctx.message.author.id)
        ret = await is_wade(ctx)
        return ret
    ret = commands.check(predicate)
    return ret

# decorator for restricting a command to only a collin, or wade
def wade_or_collinses_only():
    async def predicate(ctx):
        # log.info(ctx.message.author.id)
        ret = await is_one_of_the_collins_or_wade(ctx)
        return ret
    ret = commands.check(predicate)
    return ret

# if the user sets the bot status, this overrides the normal
# schedule for a short period of time. that status is stored
# here for that duration
USER_SET_TICKER = None

# run on a loop to update the bot status ticker
# loops through a list of statuses (which can be added to via
# the "bb status" command), visiting each one for a short time.
# appends "(at night)" to the status string if there are
# active SSH sessions (i.e. the bot is under maintenance)
async def update_status(bot, force_message=None):
    if not bot:
        log.warn("Bot not provided.")
        return

    try:
        global USER_SET_TICKER
        TICKER_NEXT_MSG_PERIOD = 60*5 # seconds

        if USER_SET_TICKER is not None:
            time_set = USER_SET_TICKER[1]
            age = datetime.now() - time_set
            if age > timedelta(seconds=TICKER_NEXT_MSG_PERIOD):
                log.debug(f"New message {USER_SET_TICKER[0]} has expired.")
                USER_SET_TICKER = None

        dt = timedelta(seconds=int(time.time() - psutil.boot_time()))

        activity = discord.ActivityType.playing

        msg = ""
        if force_message:
            msg = force_message
        elif USER_SET_TICKER is not None:
            msg = USER_SET_TICKER[0]
        else:
            msg = f"updog {dt}"
            TICKER_MESSAGES = get_param("ticker", [])
            i = int(dt.total_seconds() / TICKER_NEXT_MSG_PERIOD) % (len(TICKER_MESSAGES) * 2 + 1)
            if i > 0:
                i -= 1

                if i % 2 == 0:
                    msg = "DudeBot is " + ("online" if await is_dudebot_online(bot) else "offline")
                else:
                    msg = TICKER_MESSAGES[i // 2]

        if ssh_sessions():
            msg += " (at night)"
        act = discord.Activity(type=activity, name=msg)

        await bot.change_presence(activity=act)
    except AttributeError:
        pass
    except Exception as e:
        log.debug(f"Client: {bot}, activity={activity}, msg={msg}")
        log.debug(f"Failed to change presence: {type(e)} {e}")

# converts text to a google text to speech file, and returns
# the filename of the resultant file
def soundify_text(text, lang, tld):
    tts = gTTS(text=text, lang=lang, tld=tld)
    filename = tmp_fn("say", "mp3")
    tts.save(filename)
    return filename

# constructs an audio stream object from an audio file,
# for streaming via discord audio API
def file_to_audio_stream(filename):
    if os.name == "nt": # SOL
        return None
    return FFmpegPCMAudio(executable="/usr/bin/ffmpeg",
        source=filename, options="-loglevel panic")

# constructs an audio stream object from the URL
# pointing to such a stream
def stream_url_to_audio_stream(url):
    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }
    return FFmpegPCMAudio(url, **FFMPEG_OPTIONS)

# converts a youtube video URL to an audio stream object,
# or several stream objects in the case of youtube playlist URLs
def youtube_to_audio_stream(url):
    log.debug(f"Converting YouTube audio: {url}")

    # don't ask me what these mean, no one knows
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

    try:
        extracted_info = YoutubeDL(YDL_OPTIONS).extract_info(url, download=False)
    except:
        return None
    if not extracted_info:
        print("Failed to get YouTube video info.")
        return []
    to_process = []
    if "format" not in extracted_info and "entries" in extracted_info:
        print("Looks like this is a playlist.")
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

# initiates connection to a voice channel
async def join_voice(bot, ctx, channel):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if not voice or voice.channel != channel:
        if voice:
            await voice.disconnect()
        await channel.connect()

# will attempt to join a voice channel according to these strategies:
# - will try to join the VC of the requester, if relevant/possible
# - if not, will join a random populated voice channel
# - if no channels are populated, will join a random VC
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

# returns a unique filename stamped with the current time.
# good for files we want to look at later
def stamped_fn(prefix, ext, dir=GENERATED_FILES_DIR):
    if not os.path.exists(dir):
        os.mkdir(dir)
    return f"{dir}/{prefix}-{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.{ext}"

# returns a unique filename in /tmp; for temporary work
# which is not intended to persist past reboots
def tmp_fn(prefix, ext):
    return stamped_fn(prefix, ext, "/tmp/bagelbot")

# downloads a file from the given URL to a filepath destination;
# doesn't check if the destination file already exists, or if
# the path is valid at all
def download_file(url, destination):
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) " \
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    response = requests.get(url, headers=headers)
    bin = response.content
    file = open(destination, "wb")
    file.write(bin)
    file.close()

# given a directory and search key, will select a random sound file
# in the directory or any subdirectories whose filename is a fuzzy
# match for the search key. good for providing users with unstructured
# and fault-tolerant search functions for sound effect commands
def choose_from_dir(directory, *search_key):
    log.debug(f"directory: {directory}, search: {search_key}")
    files = glob(f"{directory}/*.mp3") + glob(f"{directory}/**/*.mp3") + \
            glob(f"{directory}/*.ogg") + glob(f"{directory}/**/*.ogg") + \
            glob(f"{directory}/*.wav") + glob(f"{directory}/**/*.wav")
    if not files:
        log.error(f"No files to choose from in {directory}.")
        return ""
    choice = random.choice(files)
    if search_key:
        search_key = " ".join(search_key)
        choices = process.extract(search_key, files)
        choices = [x[0] for x in choices if x[1] == choices[0][1]]
        choice = random.choice(choices)
    log.debug(f"choice: {choice}")
    return choice

# determines if a network host is up or down quickly.
# True if they're alive, False if they're dead.
def ping_host(ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.05)
        sock.connect((ip, port))
    except socket.error as e:
        return False
    return True

# computes the nth fibonacci number recursively
def fib(n):
    if n < 1:
        return 0
    if n == 1:
        return 1
    return fib(n-1) + fib(n-2)

# asks a humorous web API for an ad string
def get_advertisement():
    try:
        r = requests.get(f"https://api.isevenapi.xyz/api/iseven/2/")
        d = r.json()
        return d["ad"]
    except Exception:
        return None


def git_commit_all_changes(directory, message):

    print(f"Commiting changes in {directory} with message \"{message}\"")
    cmds = [
        ["git", "add", "."],
        ["git", "commit", "-m", message],
        ["git", "push"]
    ]
    for cmd in cmds:
        Popen(cmd, cwd=directory, stdout=sys.stdout, stderr=sys.stderr).communicate()


class Debug(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.log_dumper.start()
        # self.state_backup.start() # really cool, but not the best idea
        self.force_dump = False
        self.last_dump = None
        pass

    @tasks.loop(hours=6)
    async def state_backup(self):
        pvt = WORKSPACE_DIRECTORY + "/private"
        log.info(f"State backup of {pvt} initiated.")
        msg = f"Automatic state backup at {datetime.now()}."
        git_commit_all_changes(pvt, msg)

    # update loop which dumps the daily logfile (log.txt) to the
    # discord server logging channel, as well as appends the daily
    # file to the archive log. clears the daily log once complete.
    # additionally, a user can force an off-schedule dump by setting
    # self.force_dump to True
    @tasks.loop(seconds=30)
    async def log_dumper(self):

        await update_status(self.bot)

        if not self.last_dump:
            self.last_dump = datetime.now()
            return
        now = datetime.now()

        next_dump = self.last_dump.replace( \
            hour=11, minute=0, second=0, microsecond=0)
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

        log_channel = get_log_channel(self.bot)
        if not log_channel:
            log.warn("Failed to acquire handle to log dump channel. Retrying in 120 seconds...")
            await asyncio.sleep(120)
            log_channel = get_log_channel(self.bot)
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

    @commands.command(help="Get an invite link for this bot.")
    async def invite(self, ctx):
        link = "https://discord.com/oauth2/authorize?client_id=421167204633935901&permissions=378061188160&scope=bot"
        await ctx.send(link)

    # sets force_dump to True, so the log dumper loop will
    # see this on its next run and dump the daily log
    # off-schedule. only wade can run this command
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

    # I feel I should note that I essentially never throw
    # exceptions in my actual programs because they are a truly
    # terrible way to handle off-nominal conditions. but other
    # people throw them all the time, so this tests the bot's
    # ability to handle unforeseen circumstances
    @commands.command(help="Throw an error for testing.")
    async def error(self, ctx):
        raise Exception("This is a fake error for testing.")

    # obviously, only wade should be able to run this
    @commands.command(help="Test for limited permissions.")
    @wade_only()
    async def only_wade(self, ctx):
        await ctx.send("Wanker.")

    @commands.command(help="Test for permissions for the nuclear codes.")
    @wade_or_collinses_only()
    async def only_collinses(self, ctx):
        await ctx.send("Tactical nuke incoming.")

    # part of a demonstration of the bot's ability to use remote
    # endpoints as part of its available compute resources. this command
    # just tests to see if other endpoints are available
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

    # part of a demonstration of the bot's ability to use remote
    # endpoints as part of its available compute resources.
    # this will run a very inefficient fibonacci computation on the
    # host computer (probably a raspberry pi 3), and then on
    # any available network endpoints (other PCs running a compatible
    # XMLRPC server). Computation times are included to demonstrate
    # the entire point of this endeavor, which is to take advantage
    # of faster hardware that may be intermittently available via
    # the local area network
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
                log.warning(f"Not available: {hostname}:{port}")
                continue
            s = xmlrpc.client.ServerProxy(f"http://{hostname}:{port}")
            start = datetime.now()
            k = s.fib(n)
            end = datetime.now()
            await ctx.send(f"{hostname}:{port}: fib({n}) = {k}. {end - start}")

    # bug report command. allows users to report bugs, with the
    # option to include a screen capture of the issue.
    # copies the report locally on the filesystem, and
    # forwards the report to a designated bug report channel
    # on the development server
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



# the raison d'etre of this bot... bagels
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
        log.debug(f"Enqueueing audio: guild={guild}, audio={queued_audio.name}")
        self.queues[guild].queue.append(queued_audio)

    @tasks.loop(seconds=2)
    async def audio_driver(self):
        try:
            for guild, audio_queue in self.queues.items():
                voice = get(self.bot.voice_clients, guild=guild)
                members = []
                if voice:
                    members = [str(await self.bot.fetch_user(x)) for x in \
                        voice.channel.voice_states.keys() if x != self.bot.user.id]
                np = await self.get_now_playing(guild)
                if np:
                    audio_queue.now_playing = np
                    audio_queue.last_played = datetime.now()
                    if members:
                        memstr = ", ".join(members)
                        print(f"{audio_queue.last_played}: {guild} " \
                            f"({memstr}) is playing {np.name}.")
                    else:
                        print(f"{audio_queue.last_played}: {guild} " \
                            f"is playing {np.name} for nobody.")
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
                if not audio_queue.queue:
                    continue
                if voice and (voice.is_playing() or voice.is_paused()):
                    continue
                log.debug("New jobs for the audio queue.")
                to_play = audio_queue.queue.popleft()
                log.info(f"Handling queue element: guild={to_play.context.guild}, audio={to_play.name}")
                await ensure_voice(self.bot, to_play.context)
                voice = get(self.bot.voice_clients, guild=to_play.context.guild)
                if not voice:
                    log.error(f"Failed to connect to voice when trying to play {to_play}")
                    continue
                if to_play.reply_to:
                    embed = discord.Embed(title=to_play.name, color=0xff3333)
                    embed.set_author(name=to_play.context.author.name, icon_url=to_play.context.author.avatar_url)
                    file = discord.File(PICTURE_OF_BAGELS, filename="bagels.jpg")
                    embed.set_thumbnail(url="attachment://bagels.jpg")
                    if to_play.pretty_url:
                        embed.add_field(name="Now Playing", value=to_play.pretty_url)
                    maybe_ad = get_advertisement()
                    if maybe_ad:
                        embed.set_footer(text=maybe_ad)
                        log.debug(f"Delivering ad: {maybe_ad}")
                    await to_play.context.reply(embed=embed, file=file, mention_author=False)
                if to_play.source.path is not None:
                    audio = file_to_audio_stream(to_play.source.path)
                    if not audio:
                        log.error(f"Failed to convert from file (probably on Windows): {to_play.name}")
                        continue
                elif to_play.source.url is not None:
                    audio = stream_url_to_audio_stream(to_play.source.url)
                else:
                    log.error(f"Bad audio source: {to_play.name}")
                    continue
                print(f"{guild} is playing {to_play.name}")
                audio_queue.playing_flag = True
                audio_queue.last_played = datetime.now()
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

    @commands.command(name="now-playing", aliases=["np", "shazam"], help="What song/ridiculous Star Wars quote is this?")
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
        await self.enqueue_audio(QueuedAudio(f"Say: {say}", None, source, ctx))

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
        qa = QueuedAudio(filename, None, source, ctx, False, True)
        await self.enqueue_audio(qa)
        # await asyncio.sleep(3)
        # while await self.get_now_playing(ctx.guild):
        #     await asyncio.sleep(0.2)
        #     print("Waiting to finish...")
        # await voice.disconnect()

    @commands.command(help="It's time to go to bed!")
    async def bedtime(self, ctx):
        log.debug(f"{ctx.message.author} wants everyone to go to bed.")
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        members = []
        if voice:
            members = [str(await self.bot.fetch_user(x)) for x in \
                voice.channel.voice_states.keys() if x != self.bot.user.id]
        log.debug(f"Voice members: {members}")
        if not members:
            await ctx.send("Nobody in voice!")
            return
        await ctx.send("It's time for bed!")

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
        await self.enqueue_audio(QueuedAudio(f"{filename} (effect)", None, source, ctx))

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

    @commands.command(help="Nice on!")
    async def wii(self, ctx, *search):
        choice = choose_from_dir(WII_EFFECTS_DIR, *search)
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

    @commands.command(help="Buuuhhhh.")
    async def buh(self, ctx):
        await self.generic_sound_effect_callback(ctx, BUHH_PATH)

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
            # await self.enqueue_audio(QueuedAudio(f"{title} (<{info['webpage_url']}>)", source, ctx, True))
            await self.enqueue_audio(QueuedAudio(title, info["webpage_url"], source, ctx, True))


class Miscellaneous(commands.Cog): 

    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Test for invoking DudeBot.")
    async def dude(self, ctx):
        await ctx.send("Dude.")

    @commands.command(name="annoy-smith", help="Annoy Smith.")
    async def annoy_smith(self, ctx):
        for i in range(5):
            await ctx.send(".rgb 255 255 255")
            await asyncio.sleep(1)
            await ctx.send(".rgb off")
            await asyncio.sleep(1)
        await ctx.send("Done annoying Smith.")

    @commands.command(help="Add a status message to BagelBot.")
    async def status(self, ctx, *message):
        if not message:
            await ctx.send("Please provide a status message for this command.")
            return
        global USER_SET_TICKER
        message = " ".join(message)
        log.debug(f"{ctx.message.author} is adding a status: {message}")
        tickers = get_param("ticker", [])
        tickers.append(message)
        set_param("ticker", tickers)
        USER_SET_TICKER = (message, datetime.now())
        await ctx.send(f"Thanks, your message \"{message}\" will be seen by literally several people.")
        await update_status(self.bot, message)

    @commands.command(name="even-odd", help="Check if a number is even or odd.")
    async def even_odd(self, ctx, num: int):
        r = requests.get(f"https://api.isevenapi.xyz/api/iseven/{num}/")
        d = r.json()
        ad = d["ad"]
        iseven = d["iseven"]
        even_or_odd = "even" if iseven else "odd"

        embed = discord.Embed(title=f"Is {num} even or odd?",
            description=f"Your number is {even_or_odd}.", color=0xff3333)
        embed.add_field(name="Number", value=str(num), inline=False)
        embed.add_field(name="Result", value=even_or_odd.capitalize(), inline=False)
        embed.add_field(name="Advertisement", value=ad, inline=False)
        await ctx.send(embed=embed)

    @commands.command(help="Get the current time.")
    async def time(self, ctx):
        await ctx.send("It's Hubble Time.")

    @commands.command(help="Get the definition of a word.")
    async def define(self, ctx, *message):
        word = " ".join(message)
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
            return
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

    @commands.command(help="Add some anti-fascism to pictures of you and your friends!")
    async def gritty(self, ctx, *options):
        log.debug(f"{ctx.message.author} wants to be gritty, opts={options}.")
        if not ctx.message.attachments:
            await ctx.send("Please attach at least one image to add Gritty to.")
            return

        opts = {}
        for o in options:
            try:
                if "=" not in o:
                    await ctx.send(f"Malformed parameter: `{o}`. Parameters look like `key=value`.")
                    return
                k, v = o.split("=")
                if v.isdigit():
                    opts[k] = int(v)
                else:
                    opts[k] = float(v)
            except:
                await ctx.send(f"Malformed parameter: `{o}`. Parameters look like `key=value`.")
                return
        
        invalid_keys = [x for x in opts.keys() if x not in ["scale", "neighbors", "size"]]
        if invalid_keys:
            invalid_keys = [f'`{x}`' for x in invalid_keys]
            await ctx.send(f"These parameters are invalid: {' '.join(invalid_keys)}. " \
                f"Valid keys are `scale`, `neighbors`, and `size`.")
            return

        log.debug(f"Successfully parsed options: {opts}.")

        images_to_process = []

        for att in ctx.message.attachments:
            dl_filename = "/tmp/" + att.filename.lower()
            if any(dl_filename.endswith(image) for image in ["png", "jpeg", "gif", "jpg"]):
                log.debug(f"Saving image attachment to {dl_filename}")
                await att.save(dl_filename)
                images_to_process.append(dl_filename)
            else:
                log.warning(f"Not saving attachment of unsupported type: {dl_filename}.")
                dl_filename = None

        if not images_to_process:
            await ctx.send("No image attachments found. This command can only operate on images.")
            return

        for img_path in images_to_process:
            out_path = stamped_fn("gritty", "jpg")
            if do_gritty(img_path, out_path, opts):
                await ctx.send(file=discord.File(out_path))
            else:
                await ctx.send("Hmm, I couldn't find any faces in this image.")

    @commands.command(help="Get a GIF.")
    async def gif(self, ctx, *to_translate):
        if not to_translate:
            log.debug(f"{ctx.message.author} wants a GIF.")
            url = giphy.random("bagels")
            await ctx.send(url)
            return
        to_translate = " ".join(to_translate)
        log.debug(f"{ctx.message.author} wants a GIF for message {to_translate}.")
        url = giphy.translate(to_translate)
        log.debug(f"Choice is {url}.")
        await ctx.send(url)

    @commands.command(help="Get a dog picture.")
    async def dog(self, ctx):
        log.debug(f"Delivering a dog picture.")
        files = glob(f"{DOG_PICS_DIR}/*.jpg")
        if not files:
            log.error(f"No files to choose from in {DOG_PICS_DIR}.")
            await ctx.send("Woops, I couldn't find any dog pics to show you. This is an error.")
            return
        choice = random.choice(files)
        log.debug(f"choice: {choice}")
        await ctx.send(file=discord.File(choice))


class Camera(commands.Cog):

    def __init__(self, bot, still, video):
        self.bot = bot
        self.STILL_RESOLUTION = still
        self.VIDEO_RESOLUTION = video
        self.camera = picamera.PiCamera()
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
        await ctx.send(f"Recording for {seconds} seconds.")
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
        files = glob(GENERATED_FILES_DIR + "/sunrise*.jpg")
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


def reminder_msg(mention, thing_to_do, date, is_channel, snooze_delta, snooze_times):
    snooze_text = ""
    if snooze_times == 1:
        snooze_text = f" (Snoozed {snooze_times} time.)"
    elif snooze_times:
        snooze_text = f" (Snoozed {snooze_times} times.)"
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
    return random.choice(choices) + snooze_text


async def is_dudebot_online(client):

    DUDEBOT_ID = 934972571647090710
    user = get(client.get_all_members(), id=DUDEBOT_ID)
    if user:
        return str(user.status) == "online"
    return False


class Productivity(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.reminders = get_param("reminders", [])
        # self.process_reminders.start()
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

    # @commands.command(help="Slip into ya dms.")
    async def remind_old(self, ctx, channel_or_user: Union[discord.TextChannel, discord.Member, None], *unstructured_garbage):

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
        daily = any(x in arg for x in ["everyday", "every day", "daily"])
        if daily:
            log.debug(f"Requesting daily reminder: {arg}")
        if arg.startswith("me "):
            arg = arg[3:]
        pattern = r"(.+)\s(\bat\b\s.+|\bby\b\s.+|\bon\b\s.+|\bin\b\s.+)"
        matches = re.search(pattern, arg)
        if not matches:
            log.debug(f"Request didn't match regex pattern: {arg}")
            await ctx.send("Sorry, I couldn't understand that. (Couldn't find a date.) " \
                "Please phrase your remindme request like this:\n" \
                "```bb remindme to do the dishes by tomorrow```" \
                "```bb remindme to do my homework in 4 days```"
                "```bb remindme view the quadrantids meteor shower on January 2, 2022, 1 am```"
                "```bb remindme eat a krabby patty at 3 am```")
            return
        thing_to_do = matches.group(1)
        datestr = matches.group(2)
        date = dparse(datestr)
        if not date:
            await ctx.send(f"Sorry, I couldn't understand that. (Bad date: \"{datestr}\".) " \
                "Please phrase your remindme request like this:\n" \
                "```bb remindme [thing to do] [when to do it]```" \
                "```bb remindme to do the dishes by tomorrow```" \
                "```bb remindme to do my homework in 4 days```"
                "```bb remindme view the quadrantids meteor shower on January 2, 2022, 1 am```"
                "```bb remindme eat a krabby patty at 3 am```")
            return
        datestr = date.strftime('%I:%M %p on %B %d, %Y')
        if daily:
            datestr = f"{date.strftime('%I:%M %p')} every day starting on {date.strftime('%B %d, %Y')}"

        noun = "you"
        if channel_or_user:
            noun = channel_or_user.mention

        log.debug(f"thing={thing_to_do}, datestr={datestr}, date={date}")
        msg = await ctx.send(f"You want me to remind {noun} to **{realign_tense_of_task(thing_to_do)}** " \
            f"at **{datestr}**. Is this correct?", allowed_mentions=am)

        reaction = await prompt_user_to_react_on_message(self.bot, msg, ctx.message.author, ["✅", "❌"], 30)
        if not reaction:
            await msg.edit(content=f"Ok, I won't remind {noun} to " \
                f"**{realign_tense_of_task(thing_to_do)}** " \
                f"at **{datestr}**.", allowed_mentions=am)
            await clear_as_many_emojis_as_possible(msg)
            return
        await clear_as_many_emojis_as_possible(msg)

        success = str(reaction.emoji) == "✅"
        if not success:
            await msg.edit(content=f"Ok, I won't remind {noun} to " \
                f"**{realign_tense_of_task(thing_to_do)}**.", allowed_mentions=am)
            return

        if date < datetime.now():
            await msg.edit(content=f"Sorry, I can't remind {noun} to " \
                f"**{realign_tense_of_task(thing_to_do)}** " \
                f"at **{datestr}**, " \
                "since the specified time is in the past.", allowed_mentions=am)
            return

        await msg.edit(content=f"Gotcha, I'll remind {noun} to " \
            f"**{realign_tense_of_task(thing_to_do)}** " \
            f"at **{datestr}**.", allowed_mentions=am)

        reminder = {"thing": thing_to_do, "datetime": date,
            "user": user_to_remind, "channel": channel_id,
            "requested_by": requested_by, "daily": daily}
        reminder_database = get_param("reminders", [])
        reminder_database.append(reminder)
        set_param("reminders", reminder_database)
        self.reminders = reminder_database

    @tasks.loop(seconds=10)
    async def process_reminders(self):

        am = discord.AllowedMentions(users=False)
    
        snooze_durations = {
            ""
            "🕐": timedelta(minutes=5),
            "🕒": timedelta(minutes=15),
            "🕔": timedelta(minutes=30),
            "🕖": timedelta(hours=1),
            "🕙": timedelta(hours=4),
            "⏳": timedelta(days=1)
        }

        am = discord.AllowedMentions(users=False)
        write_to_disk = False
        for rem in self.reminders:
            if "snooze" not in rem:
                rem["snooze"] = 0
            if "times_snoozed" not in rem:
                rem["times_snoozed"] = 0
            snooze_delta = timedelta(seconds=rem["snooze"])
            date = rem["datetime"] + snooze_delta
            daily = rem["daily"]
            thing_to_do = rem["thing"]
            if date <= datetime.now():
                target_reactions_from = None
                if rem["user"]:
                    is_channel = False
                    handle = await self.bot.fetch_user(rem["user"])
                    target_reactions_from = handle
                else:
                    handle = await self.bot.fetch_channel(rem["channel"])
                    is_channel = True
                write_to_disk = True
                log.info(f"Reminding {handle}: {thing_to_do}")
                text = reminder_msg(handle.mention, thing_to_do, date, is_channel, snooze_delta, rem["times_snoozed"])
                msg = await handle.send(text, allowed_mentions=am)
                reaction = await prompt_user_to_react_on_message(self.bot,
                    msg, target_reactions_from, ["✅", "🕐", "🕒", "🕔", "🕖", "🕙", "⏳"], 30)
                if reaction and reaction.emoji != "✅":
                    snooze_dur = snooze_durations[reaction.emoji]
                    log.debug(f"Remindee selected this option: {reaction}, for snooze {snooze_dur}")
                    rem["snooze"] += snooze_dur.total_seconds()
                    rem["times_snoozed"] = rem["times_snoozed"] + 1
                    deltastr = strftimedelta(snooze_dur)
                    await msg.edit(content=f"Ok, I'll remind you to do that again in {deltastr}.",
                        allowed_mentions=am)
                elif daily:
                    date += timedelta(hours=24)
                    log.debug(f"For daily reminder {rem}, setting new reminder time to {date}.")
                    rem["datetime"] = date
                    rem["snooze"] = 0
                    rem["times_snoozed"] = 0
                else:
                    rem["complete"] = True
                    log.debug("Marking this as complete.")
                await clear_as_many_emojis_as_possible(msg)
        self.reminders = [x for x in self.reminders if "complete" not in x]
        if write_to_disk:
            set_param("reminders", self.reminders)

    # @commands.command(name="show-reminders", aliases=["sr"], help="Show your pending reminders.")
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


async def report_error_occurred(bot, ctx, e):
    await ctx.send(f"Oof, ouch, my bones. Encountered an internal error. ({e})")
    await ctx.send(random.choice(giphy.search("error")), delete_after=30)
    msg = ctx.message
    errstr = format_exception(type(e), e, e.__traceback__)
    errstr = "\n".join(errstr)
    s = f"Error: {type(e).__name__}: {e}\n{errstr}\n"
    fmted = f"{msg.guild} {msg.channel} {msg.author} {msg.content}:\n{s}"
    log.error(fmted)
    bug_report_channel = bot.get_channel(908165358488289311)
    if not bug_report_channel:
        log.error("Failed to acquire handle to bug report channel!")
        return

    embed = discord.Embed(title="Error Report",
        description=f"Error of type {type(e).__name__} has occurred.",
        color=discord.Color.red())
    embed.add_field(name="Server", value=f"{msg.guild}", inline=True)
    embed.add_field(name="Channel", value=f"{msg.channel}", inline=True)
    embed.add_field(name="Author", value=f"{msg.author}", inline=True)
    embed.add_field(name="Message", value=f"{msg.content}", inline=False)
    embed.add_field(name="Full Exception", value=f"{e}", inline=False)
    file = discord.File(DUMB_FISH_PATH, filename="fish.png")
    embed.set_thumbnail(url="attachment://fish.png")
    await bug_report_channel.send(file=file, embed=embed)


async def report_haiku(bot, msg):
    bug_report_channel = bot.get_channel(908165358488289311)
    if not bug_report_channel:
        log.error("Failed to acquire handle to bug report channel!")
        return

    embed = discord.Embed(title="Haiku Detected",
        description=f"{msg.author} has written a haiku!",
        color=discord.Color.blue())
    embed.add_field(name="Server", value=f"{msg.guild}", inline=True)
    embed.add_field(name="Channel", value=f"{msg.channel}", inline=True)
    embed.add_field(name="Author", value=f"{msg.author}", inline=True)
    embed.add_field(name="Message", value=f"{msg.content}", inline=False)
    await bug_report_channel.send(embed=embed)


def main():

    STILL_RES = (3280, 2464)
    VIDEO_RES = (1080, 720)
    intents = discord.Intents.default()
    intents.members = True
    intents.presences = True
    bagelbot = commands.Bot(command_prefix=["Bb ", "bb ", "BB "],
        case_insensitive=True, intents=intents)

    @bagelbot.event
    async def on_ready():
        print("Connected.")
        log.info("Connected.")
        await update_status(bagelbot)

    @bagelbot.event
    async def on_command_error(ctx, e):
        if type(e) is discord.ext.commands.errors.CommandNotFound:
            await ctx.send("That's not a command; I don't know what you're on about.")
            await ctx.send(random.choice(giphy.search("confused")), delete_after=30)
            return
        if type(e) is discord.ext.commands.errors.CheckFailure:
            await ctx.send("Hey, you don't have sufficient permissions to use that command.")
            await ctx.send(random.choice(giphy.search("denied")), delete_after=30)
            return
        if type(e) is discord.ext.commands.errors.BadArgument:
            await ctx.send(f"Sorry, you've provided bad arguments for that command.")
            await ctx.send(random.choice(giphy.search("bad")), delete_after=30)
            return
        if type(e) is discord.ext.commands.errors.MissingRequiredArgument:
            await ctx.send(f"You're missing a required argument for that command.")
            await ctx.send(random.choice(giphy.search("gone")), delete_after=30)
            return
        await report_error_occurred(bagelbot, ctx, e)

    @bagelbot.event
    async def on_command(ctx):
        msg = ctx.message
        log.debug(f"{msg.guild} {msg.channel} {msg.author} {msg.content}")

    @bagelbot.event
    async def on_message(message):
        if message.author == bagelbot.user:
            return

        # handle the case where some keyboards provide a ’ for
        # apostrophies instead of the typical ' ...
        # ord("’") == 8217
        # ord("'") == 39
        message.content = message.content.replace("’", "'")

        cleaned = message.content.strip().lower()
        words = cleaned.split()

        song_responses = singalong(str(message.guild), cleaned)
        haiku = detect_haiku(cleaned)
        words = [x.lower() for x in words if len(x) > 9 and x[0].lower() != 'b' and x.isalpha()]
        if song_responses:
            log.debug(f"Decided to sing along with {message.author}.")
            for resp in song_responses:
                await message.channel.send(resp)
        elif haiku:
            log.info(f"{message.author}'s message \"{cleaned}\" is a haiku!\n  {haiku}")
            await message.channel.send(f"...\n*{haiku[0]}*\n*{haiku[1]}*\n*{haiku[2]}*\n" + \
                f"- {message.author.name}")

            await report_haiku(bagelbot, message)

            try:
                text_channel_list = []
                recorded = False
                for channel in message.guild.channels:
                    if str(channel.type) == 'text' and channel.name == "technically-a-haiku":
                        await channel.send(f"...\n*{haiku[0]}*\n*{haiku[1]}*\n*{haiku[2]}*\n" + \
                            f"- {message.author.name}")
                        log.debug(f"Recorded in {channel}.")
                        recorded = True
                if not recorded:
                    log.debug("Not recorded, since no appropriate channel exists.")
            except Exception as e:
                log.error(f"Threw exception trying to record haiku: {e}")
   
        elif "too hot" in cleaned:
            log.info(f"{message.author}'s message is too hot!: {cleaned}")
            log.info("Hot damn.")
            await message.channel.send("*𝅗𝅥 Hot damn 𝅘𝅥*")
        elif words and random.random() < 0.01:
            selection = random.choice(words)
            log.debug(f"trying b-replacement: {selection}")
            if selection.startswith("<@"): # discord user mention
                log.debug(f"'{selection}' is a user mention or emoji.")
            elif validators.url(selection):
                log.debug(f"'{selection}' is a URL.")
            else:
                if selection[0] in ['a', 'e', 'i', 'o', 'u', 'l', 'r']:
                    make_b = "B" + selection
                else:
                    make_b = "B" + selection[1:]
                if make_b[-1] != ".":
                    make_b = make_b + "."
                log.debug(f"Doing it to {message.author}: {make_b}")
                await message.channel.send(make_b)
        elif random.random() < 0.001:
            log.info(f"Giving a stupid fish to {message.author}.")
            await message.reply(file=discord.File(DUMB_FISH_PATH))
        elif random.random() < 0.001:
            w = get_wisdom()
            log.debug(f"Sending unsolicited wisdom to {message.author}: {w}")
            await message.channel.send(w)

        # TODO: make this only work near collin smith's birthday
        # -- is that a security issue?

        # maybe_quote = get_quote(message.content.strip())
        # if maybe_quote:
        #     await message.channel.send(maybe_quote)
        # birthday_dialects = ["birth", "burf", "smeef", "smurf"]
        # to_mention = message.author.mention
        # if message.mentions:
        #     to_mention = message.mentions[0].mention
        # for dialect in birthday_dialects:
        #     if dialect in cleaned:
        #         await message.channel.send(f"Happy {dialect}day, {to_mention}!")
        #         break

        await bagelbot.process_commands(message)

    bagelbot.add_cog(Debug(bagelbot))
    bagelbot.add_cog(Bagels(bagelbot))
    bagelbot.add_cog(Voice(bagelbot))
    if picamera:
        bagelbot.add_cog(Camera(bagelbot, STILL_RES, VIDEO_RES))
    bagelbot.add_cog(Miscellaneous(bagelbot))
    bagelbot.add_cog(Productivity(bagelbot))
    bagelbot.add_cog(Farkle(bagelbot))
    bagelbot.add_cog(RemindV2(bagelbot))
    bagelbot.add_cog(Othello(bagelbot))
    bagelbot.run(get_param("DISCORD_TOKEN"))



if __name__ == "__main__":
    main()

