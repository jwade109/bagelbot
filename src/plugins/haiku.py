#! /usr/bin/env python3

from bagelshop.logging import log
from ws_dir import WORKSPACE_DIRECTORY
from state_machine import get_param, set_param
from bot_common import DONT_ALERT_USERS

import bagelshop.haiku as bsh


HAIKU_PARAM_NAME = "haiku_leaderboard"
HAIKU_YAML_PATH = WORKSPACE_DIRECTORY + "/private/haiku.yaml"


import discord
from discord.ext import commands


HAIKU_ALERTS_CHANNEL_ID = 908165358488289311


async def report_haiku(bot, msg):
    bug_report_channel = bot.get_channel(HAIKU_ALERTS_CHANNEL_ID)
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

        if message.author == self.bot.user:
            return

        cleaned = message.content.strip().lower()
        haiku = bsh.detect_haiku(cleaned)

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
