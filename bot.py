#! /usr/bin/env python3

print("Starting bagelbot...")

import os
import logging

log_filename = "/home/pi/bagelbot/log.txt"
logging.basicConfig(filename=log_filename,
    level=logging.INFO, format="%(levelname)-10s %(asctime)-25s %(name)-22s %(funcName)-18s // %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("bagelbot")
log.setLevel(logging.DEBUG)

log.info("STARTING. =============================")
print(f"Writing to {log_filename}")

import sys
import discord
import re
import random
import asyncio
from glob import glob
from pathlib import Path
from traceback import format_exception
import yaml
from animals import Animals
from cowpy import cow
from datetime import datetime, timedelta
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
from dataclasses import dataclass
from typing import Union
from collections import deque
import socket
import xmlrpc.client
import validators # for checking if string is a URL
from gibberish import Gibberish as gib
gib = gib() # you've got to be kidding me with this object-oriented BS, seriously
import randomname # for generating bug ticket names

def get_bug_ticket_name():
    return randomname.get_name(adj=('physics'), noun=('dogs')) + \
        "-" + str(random.randint(100, 1000))

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

print("Done importing things.")

def check_exists(path):
    if not os.path.exists(path):
        print(f"WARNING: required path {path} doesn't exist!")
    return path

YAML_PATH = check_exists("/home/pi/bagelbot/bagelbot_state.yaml")
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
BUG_REPORT_DIR = check_exists("/home/pi/.bagelbot/bug-reports")

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
    log.warning(f"Failed to get parameter {name}, using default: {default}")
    set_param(name, default)
    return default


async def is_wade(ctx):
    is_wade = ctx.message.author.id == 235584665564610561
    return is_wade


async def is_one_of_the_collins_or_wade(ctx):
    is_a_collin_or_wade = await is_wade(ctx) or ctx.message.author.id == 188843663680339968 or ctx.message.author.id == 221481539735781376
    return is_a_collin_or_wade


def wade_only():
    async def predicate(ctx):
        log.info(ctx.message.author.id)
        ret = await is_wade(ctx)
        if not ret:
            await ctx.send("Hey, you're not Wade.")
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
        # bagels = get_param("num_bagels", 0)
        # prefix = "anti" if bagels < 0 else ""
        # act = discord.Activity(type=discord.ActivityType.watching,
        #                        name=f" {abs(bagels):0.2f} {prefix}bagels")
        act = discord.Activity(type=discord.ActivityType.watching,
                               name=f" for some fried chicken")
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
        print(e)
        return False
    return True


def fib(n):
    if n < 1:
        return 0
    if n == 1:
        return 1
    return fib(n-1) + fib(n-2)


class Debug(commands.Cog):

    def __init__(self):
        pass

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
                print(f"Not available: {hostname}:{port}")
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
        info_file.write(f"Time: {datetime.now()}\n")
        info_file.close()

        await ctx.send(f"Thanks for submitting a bug report. Your ticket is: {ticket_name}")

        if msg.attachments:
            log.debug(f"Bug report directory: {bug_dir}")
            for att in msg.attachments:
                dl_filename = bug_dir + "/" + att.filename.lower()
                if any(dl_filename.endswith(image) for image in ["png", "jpeg", "gif", "jpg"]):
                    log.debug(f"Saving image attachment to {dl_filename}")
                    await att.save(dl_filename)
                else:
                    log.warn(f"Not saving attachment of unsupported type: {dl_filename}.")



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
        await update_status(self.bot)

    @commands.command(help="Check how many bagels there are.")
    async def bagels(self, ctx):
        bagels = int(get_param("num_bagels", 0))
        if bagels == 1:
            await ctx.send(f"There is 1 lonely bagel.")
        elif bagels == 69:
            await ctx.send(f"There are 69 bagels. Nice.")
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
            print(f"New guild audio queue: {guild}")
            log.debug(f"New guild audio queue: {guild}")
            self.queues[guild] = deque()
        if len(self.queues[guild]) < 10:
            print(f"Enqueueing audio: guild={guild}, audio={queued_audio}")
            log.debug(f"Enqueueing audio: guild={guild}, audio={queued_audio}")
            self.queues[guild].append(queued_audio)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not member.id == self.bot.user.id:
            return
        elif before.channel is None:
            # log.debug(f"State update: {member}, {before}, {after}")
            voice = after.channel.guild.voice_client
            time = 0
            wait = 5 # seconds
            disconnect_after = 60 * 5 # 5 minutes
            while True:
                await asyncio.sleep(wait)
                time = time + wait
                if voice.is_playing() and not voice.is_paused():
                    time = 0
                if time >= disconnect_after:
                    await voice.disconnect()
                if not voice.is_connected():
                    break

    @tasks.loop(seconds=2)
    async def audio_driver(self):
        try:
            for guild, audio_queue in self.queues.items():
                np = await self.get_now_playing(guild)
                if np:
                    print(f"{datetime.now()}: {guild} is playing {np.name}")
                if not audio_queue:
                    continue
                voice = get(self.bot.voice_clients, guild=guild)
                if voice and (voice.is_playing() or voice.is_paused()):
                    continue
                print("New jobs for the audio queue.")
                to_play = audio_queue.popleft()
                print(f"Handling queue element: guild={to_play.context.guild}, audio={to_play}")
                await ensure_voice(self.bot, to_play.context)
                voice = get(self.bot.voice_clients, guild=to_play.context.guild)
                if not voice:
                    print("Failed to connect to voice!")
                    continue
                if to_play.reply_to:
                    await to_play.context.reply(f"Now playing: {to_play.name}", mention_author=False)
                if to_play.source.path is not None:
                    audio = file_to_audio_stream(to_play.source.path)
                elif to_play.source.url is not None:
                    audio = stream_url_to_audio_stream(to_play.source.url)
                else:
                    print(f"Bad audio source: {to_play}")
                    continue
                voice.play(audio)
                self.now_playing[guild] = to_play
        except Exception as e:
            uhoh = f"VERY VERY BAD: Uncaught exception: {type(e)} {e}"
            print(uhoh)
            log.error(uhoh)

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
            self.queues[ctx.guild] = deque()
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
        for i, audio in enumerate(queue):
            line = f"{i+1:<12}{audio.name}"
            lines.append(line)
        await ctx.send("```\n===== SONG QUEUE =====\n\n" + "\n".join(lines) + "\n```")

    @commands.command(name="clear-queue", aliases=["clear", "cq"], help="Clear the song queue.")
    async def clear_queue(self, ctx):
        if ctx.guild not in self.queues or not self.queues[ctx.guild]:
            await ctx.send("Nothing currently queued!", delete_after=5)
            return
        self.queues[ctx.guild].clear()
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
        qa = QueuedAudio(filename, source, ctx)
        qa.disconnect_after = True
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
            await self.enqueue_audio(QueuedAudio(f"{title} ({info['webpage_url']})", source, ctx, True))


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
        meaning = PyDictionary().meaning(word)
        if not meaning:
            await ctx.send(f"Sorry, I couldn't find a definition for '{word}'.")
            return
        print(meaning)
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


class Productivity(commands.Cog):

    def __init__(self):
        # self.check_time.start()
        self.reminders = []
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
            await ctx.send("`bb todo` requires a subcommand. Valid subcommands are: `show`, `add`, `del`.")
            return
        subcommand = varargs[0]
        varargs = varargs[1:]

        if subcommand == "show":
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
            if not varargs:
                await ctx.send("I can't add nothing to your to-do list!")
                return
            self.add(id, " ".join(varargs))
            await ctx.send("Ok, I've added that to your to-do list.")
            return
        if subcommand == "del":
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
        
        await ctx.send(f"`{subcommand}`` is not a valid todo command. Valid subcommands are: `show`, `add`, `del`.")
        

    # @tasks.loop(minutes=1)
    # async def check_time(self):
    #     log.debug(f"Current time is {datetime.now()}.")

    # @commands.command(help="Tell BagelBot to remind you of something in the future.")
    # async def remindme(self, ctx, time : datetime, *message):
    #     rem = Reminder(ctx.message.author.id, time, " ".join(message))
    #     print(rem)
    #     await ctx.send("Ok, I'll remind you to do the thing.")


import itertools
def mixedCase(*args):
    total = []
    for string in args:
        a = map(''.join, itertools.product(*((c.upper(), c.lower()) for c in string)))
        for x in list(a): total.append(x)
    return list(total)


def main():

    STILL_RES = (3280, 2464)
    VIDEO_RES = (1080, 720)
    pi_camera = picamera.PiCamera()

    bb_array = ["b"*i for i in range(2, 6)]
    prefixes = mixedCase("bagelbot", "$", *bb_array)
    prefixes = [x + " " for x in prefixes]
    bagelbot = commands.Bot(command_prefix=prefixes, case_insensitive=True)

    @bagelbot.event
    async def on_ready():
        print("Connected.")
        log.info("Connected.")
        await update_status(bagelbot)

    @bagelbot.event
    async def on_command_error(ctx, e):
        if type(e) is discord.ext.commands.errors.CommandNotFound:
            for prefix in bagelbot.command_prefix:
                text = ctx.message.content.strip()
                if text.startswith(prefix):
                    text = text[len(prefix):]
                    log.info(f"Star Wars default invokation: {text}")
                    await ctx.message.add_reaction("🇸")
                    await ctx.message.add_reaction("🇼")
                    await ctx.invoke(bagelbot.get_command('sw'), text)
                    return
        errstr = format_exception(type(e), e, e.__traceback__)
        errstr = "\n".join(errstr)
        s = f"Error: {type(e).__name__}: {e}\n```\n{errstr}\n```"
        await ctx.send(f"Error: {type(e).__name__}: {e}")
        log.error(f"{ctx.message.content}:\n{s}")

    @bagelbot.event
    async def on_message(message):
        if message.author == bagelbot.user:
            return
        words = message.content.strip().split()
        # print(gib.generate_words(len(words)))
        words = [x.lower() for x in words if len(x) > 9 and x[0].lower() != 'b']
        # print(words)
        if words and random.random() < 0.1:
            selection = random.choice(words)
            print(selection)
            if selection.startswith("<@!"): # discord user mention
                print(f"'{selection}' is a user mention.")
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
        birthday_dialects = ["birth", "burf", "smeef", "smurf"]
        to_mention = message.author.mention
        if message.mentions:
            to_mention = message.mentions[0].mention
        cleaned = message.content.strip().lower()
        for dialect in birthday_dialects:
            if dialect in cleaned:
                await message.channel.send(f"Happy {dialect}day, {to_mention}!")
                break
        await bagelbot.process_commands(message)

    bagelbot.add_cog(Debug())
    bagelbot.add_cog(Bagels(bagelbot))
    bagelbot.add_cog(Voice(bagelbot))
    bagelbot.add_cog(Camera(bagelbot, pi_camera, STILL_RES, VIDEO_RES))
    bagelbot.add_cog(Miscellaneous())
    bagelbot.add_cog(Productivity())
    bagelbot.run(get_param("DISCORD_TOKEN"))



if __name__ == "__main__":
    main()

