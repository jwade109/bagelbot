#! /usr/bin/env python3

print("Starting bagelbot...")

import os
import sys
import logging
from ws_dir import WORKSPACE_DIRECTORY
import bblog
from bblog import log

# writing daily logfile to log.txt;
# will append this file periodically to archive.txt,
# as well as dump it to the internal logging channel

# any calls to log.debug, log.info, etc. will be
# written to the daily logfile, and eventually will
# be dumped to the development server. standard
# print() calls will not be recorded in this way

LOG_FILENAME     = WORKSPACE_DIRECTORY + "/log.txt"
ARCHIVE_FILENAME = WORKSPACE_DIRECTORY + "/private/archive.txt"

bblog.copy_logs_to_file(LOG_FILENAME)

log.info("STARTING. =============================")
log.info(f"Program args: {sys.argv}")
log.info(f"CWD: {os.getcwd()}")
log.info(f"Workspace directory: {WORKSPACE_DIRECTORY}")
log.info(f"Writing to {LOG_FILENAME}")

from resource_paths import *
from predicates import *
import discord
import re
import random
import asyncio
import math
from glob import glob
from pathlib import Path
import yaml
from animals import Animals
from cowpy import cow
from datetime import datetime, timedelta
import calendar
import shutil
import pypokedex
import requests
from discord.ext import tasks, commands
import xmlrpc.client
from gibberish import Gibberish as gib
gib = gib() # you've got to be kidding me with this object-oriented BS, seriously
import randomname # for generating bug ticket names
import psutil
import time

from gritty import do_gritty

from state_machine import get_param, set_param
import giphy
import bot_common


log.info("Done importing things.")


class Debug(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.force_dump = False
        self.last_dump = None
        pass

    @commands.Cog.listener()
    async def on_ready(self):
        self.log_dumper.start()
        log.debug("Started log dump loop.")

    # update loop which dumps the daily logfile (log.txt) to the
    # discord server logging channel, as well as appends the daily
    # file to the archive log. clears the daily log once complete.
    # additionally, a user can force an off-schedule dump by setting
    # self.force_dump to True
    @tasks.loop(seconds=30)
    async def log_dumper(self):

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

        if not os.path.exists(LOG_FILENAME) or os.stat(LOG_FILENAME).st_size == 0:
            log.info("No logs emitted in the previous period.")

        log_channel = bot.get_channel(bot_common.LOGGING_CHANNEL_ID)
        if not log_channel:
            log.warn("Failed to acquire handle to log dump channel. Retrying in 120 seconds...")
            await asyncio.sleep(120)
            log_channel = bot.get_channel(bot_common.LOGGING_CHANNEL_ID)
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
            file=discord.File(LOG_FILENAME, filename=discord_fn))

        arcfile = open(ARCHIVE_FILENAME, 'a')
        logfile = open(LOG_FILENAME, 'r')
        for line in logfile.readlines():
            arcfile.write(line)
        logfile.close()
        arcfile.close()
        open(LOG_FILENAME, 'w').close()

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

        # generates a memorable-yet-random bug ticket name, something like electron-pug-892
        def get_bug_ticket_name():
            return randomname.get_name(adj=('physics'), noun=('dogs')) + \
                "-" + str(random.randint(100, 1000))

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

        bug_report_channel = self.bot.get_channel(bot_common.LOGGING_CHANNEL_ID)
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

    @commands.command(aliases=["badmath"], help="Perform mathy math on two numbers.")
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
        log.debug(data)
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



INVOKED_COMMANDS = []


async def main():

    intents = discord.Intents.all()
    bagelbot = commands.Bot(command_prefix=["Bb ", "bb ", "BB "],
        case_insensitive=True, intents=intents)

    @bagelbot.event
    async def on_ready():
        log.info("Connected.")

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

    await bot_common.deploy_with_config(bagelbot, PROD_CONFIG)

    await bagelbot.add_cog(Debug(bagelbot))
    await bagelbot.add_cog(Miscellaneous(bagelbot))
    await bagelbot.start(get_param("DISCORD_TOKEN"))



if __name__ == "__main__":
    asyncio.run(main())

