#! /usr/bin/env python3

print("Starting bagelbot...")

import os
import sys
import logging
from ws_dir import WORKSPACE_DIRECTORY
from resource_paths import *
from predicates import *

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
from discord import FFmpegPCMAudio
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
from thickofit import prompt_module_response as singalong
from remindme import Reminders
from othello import Othello
from define import Define
from voice import Voice
from holiday import Holidays
from announcements import Announcements
from astronomy import Astronomy
from haiku import Haiku
from unprompted import Unprompted
from bagels import Bagels
import bot_common
from bot_common import LOGGING_CHANNEL_ID


# get the datetime of today's sunrise; will return a time in the past if after sunrise
def get_sunrise_today(lat, lon):
    sun = suntime.Sun(lat, lon)
    now = datetime.now()
    real_sunrise = sun.get_local_sunrise_time(now).replace(tzinfo=None)
    return real_sunrise + timedelta(minutes=30)

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

print("Done importing things.")

# is it a security hazard to put the full file paths in source control?
# the world may never know

# returns a reference to the internal logging channel,
# where log files are dumped periodically
def get_log_channel(bot):
    return bot.get_channel(908161498591928383)

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

                msg = TICKER_MESSAGES[i // 2]

        act = discord.Activity(type=activity, name=msg)

        await bot.change_presence(activity=act)
    except AttributeError:
        pass
    except Exception as e:
        log.debug(f"Client: {bot}, activity={activity}, msg={msg}")
        log.debug(f"Failed to change presence: {type(e)} {e}")


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
        # self.state_backup.start() # really cool, but not the best idea
        self.force_dump = False
        self.last_dump = None
        pass

    @commands.Cog.listener()
    async def on_ready(self):
        self.log_dumper.start()
        log.debug("Started log dump loop.")

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

        global INVOKED_COMMANDS

        try:
            if INVOKED_COMMANDS:
                embed = discord.Embed(title="Recent Activity",
                    description="\n".join(INVOKED_COMMANDS))
                await log_channel.send(embed=embed)
                INVOKED_COMMANDS = []
        except Exception as e:
            log.error(f"Failed to emit commands history readout: {e}")

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
    @wade_only()
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

        bug_report_channel = self.bot.get_channel(LOGGING_CHANNEL_ID)
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


class Miscellaneous(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Test for invoking DudeBot.")
    async def dude(self, ctx):
        await ctx.send("Dude...")

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
    async def math(self, ctx, a: float, op: str, b: float):
        s = 0
        if op == "+":
            s = a + b
        elif op == "-":
            s = a - b
        elif op == "*":
            s = a * b
        elif op == "/":
            s = a / b
        elif op == "^":
            s = a ^ b
        else:
            await ctx.send(f"Error: '{op}' is not a supported math operator.")
            return
        s += random.randint(-12, 12)
        await ctx.send(f"{a:0.2f} {op} {b:0.2f} = {s:0.2f}. Thanks for playing.")

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

    def __init__(self, bot):
        self.bot = bot
        self.STILL_RESOLUTION = (3280, 2464)
        self.VIDEO_RESOLUTION = (1080, 720)
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
        to_parse, _ = result.groups(1)[0].split(".")
        stamp = datetime.strptime(to_parse, "%Y-%m-%dT%H-%M-%S")
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


DONT_ALERT_USERS = discord.AllowedMentions(users=False)


async def send_alert(bot, text):
    bug_report_channel = bot.get_channel(LOGGING_CHANNEL_ID)
    if not bug_report_channel:
        log.error("Failed to acquire handle to bug report channel!")
        return
    try:
        await bug_report_channel.send(text, allowed_mentions=DONT_ALERT_USERS)
    except Exception as e:
        log.error(f"Failed to send alert text: \"{text}\", {e}")


INVOKED_COMMANDS = []


async def main():

    intents = discord.Intents.all()
    bagelbot = commands.Bot(command_prefix=["Bb ", "bb ", "BB "],
        case_insensitive=True, intents=intents,
        help_command=bot_common.BagelHelper())

    @bagelbot.event
    async def on_ready():
        print("Connected.")
        log.info("Connected.")
        await update_status(bagelbot)

    @bagelbot.event
    async def on_command_error(ctx, e):
        # todo: stick this in a cog somehow
        await bot_common.on_command_error(bagelbot, ctx, e)

    @bagelbot.event
    async def on_command(ctx):
        msg = ctx.message
        s = f"{msg.guild} - {msg.channel} - {msg.author} - {msg.content}"
        log.debug(s)
        INVOKED_COMMANDS.append(s)

    await bagelbot.add_cog(Debug(bagelbot))
    await bagelbot.add_cog(Bagels(bagelbot))
    await bagelbot.add_cog(Voice(bagelbot))
    if picamera:
        await bagelbot.add_cog(Camera(bagelbot))
    await bagelbot.add_cog(Miscellaneous(bagelbot))
    await bagelbot.add_cog(Productivity(bagelbot))
    await bagelbot.add_cog(Farkle(bagelbot))
    await bagelbot.add_cog(Reminders(bagelbot))
    await bagelbot.add_cog(Othello(bagelbot))
    await bagelbot.add_cog(Define(bagelbot))
    await bagelbot.add_cog(Announcements(bagelbot))
    # await bagelbot.add_cog(Holidays(bagelbot))
    await bagelbot.add_cog(Astronomy(bagelbot))
    await bagelbot.add_cog(Haiku(bagelbot))
    await bagelbot.add_cog(Unprompted(bagelbot))
    await bagelbot.start(get_param("DISCORD_TOKEN"))



if __name__ == "__main__":
    asyncio.run(main())

