#! /usr/bin/env python3

import sys
from nltk.corpus import cmudict
CMU_DICT = cmudict.dict()
# for counting syllables for haiku detection
from curses.ascii import isdigit
import itertools


def detect_haiku(string):

    def count_syllables(word):
        low = word.lower()
        for c in ",!?:;.":
            low = low.replace(c, "")
        if low not in CMU_DICT:
            return None
        syl_list = [len(list(y for y in x if isdigit(y[-1]))) for x in CMU_DICT[low]]
        syl_list = list(set(syl_list))
        if not syl_list:
            return None
        return syl_list[0]

    string = string.split(" ")
    lens = [count_syllables(x) for x in string]
    if None in lens:
        return None
    cumulative = list(itertools.accumulate(lens))
    if cumulative[-1] != 17 or 5 not in cumulative or 12 not in cumulative:
        return None
    first = " ".join(string[:cumulative.index(5) + 1])
    second = " ".join(string[cumulative.index(5) + 1:cumulative.index(12) + 1])
    third = " ".join(string[cumulative.index(12) + 1:])
    return first, second, third


def main():
    msg = " ".join(sys.argv[1:])
    if not msg:
        print("Please provide a message to test.")
        return 1
    haiku = detect_haiku(msg)
    if haiku:
        print("Haiku:\n" + "\n".join(haiku))
    else:
        print("Not a haiku.")
    return 0


if __name__ == "__main__":
    exit(main())


from bblog import log
from ws_dir import WORKSPACE_DIRECTORY
from state_machine import get_param, set_param
import logging
from bot_common import DONT_ALERT_USERS


HAIKU_PARAM_NAME = "haiku_leaderboard"
HAIKU_YAML_PATH = WORKSPACE_DIRECTORY + "/private/haiku.yaml"


import discord
from discord.ext import commands, tasks
from bot_common import ALERTS_CHANNEL_ID


async def report_haiku(bot, msg):
    bug_report_channel = bot.get_channel(ALERTS_CHANNEL_ID)
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


class Haiku(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):

        cleaned = message.content.strip().lower()
        haiku = detect_haiku(cleaned)

        if not haiku:
            return False

        log.info(f"{message.author}'s message \"{cleaned}\" is a haiku!\n  {haiku}")
        await message.channel.send(f"...\n*{haiku[0]}*\n*{haiku[1]}*\n*{haiku[2]}*\n" + \
            f"- {message.author.name}")

        await report_haiku(self.bot, message)

        param = f"{HAIKU_PARAM_NAME}/{message.author.id}"
        user_info = get_param(param,
            {"name": str(message.author), "score": 0}, HAIKU_YAML_PATH)
        user_info["score"] += 1
        set_param(param, user_info, HAIKU_YAML_PATH)

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
        return True

    @commands.command()
    async def haiku(self, ctx):
        db = get_param(HAIKU_PARAM_NAME, {}, HAIKU_YAML_PATH)
        db = {uid: info for uid, info in db.items() if ctx.guild.get_member(uid)}
        if not db:
            await ctx.send("Nobody in this server has written a haiku yet.")
            return

        s = "" if len(db) == 1 else "s"
        msg = f"Haiku count for {len(db)} user{s}:\n"
        for uid, user_info in db.items():
            score = user_info["score"]
            msg += f"\n<@{uid}>: {score}"
        await ctx.send(msg, allowed_mentions=DONT_ALERT_USERS)
