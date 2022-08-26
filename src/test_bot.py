#! /usr/bin/env python3

import os
import sys
import discord
import logging
from discord.ext import commands
from state_machine import get_param
from voice import Voice
from othello import Othello
import bot_common
from announcements import Announcer, announce_to_all
from ws_dir import WORKSPACE_DIRECTORY
import randfacts


log = logging.getLogger("cc")
log.setLevel(logging.DEBUG)
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
    format="[%(levelname)s] %(message)s")


def main():

    intents = discord.Intents.default()
    intents.members = True
    intents.presences = True
    bagelbot = commands.Bot(command_prefix=["cc ", "CC ", "Cc ", "cC "],
        case_insensitive=True, intents=intents,
        help_command=bot_common.BagelHelper())

    @bagelbot.event
    async def on_ready():
        log.info("Connected.")
        await announce_to_all(bagelbot, "Redeploying.\n\n" + randfacts.get_fact())

    @bagelbot.event
    async def on_command_error(ctx, e):
        log.error(f"Error: {e}")
        await ctx.send(f"Error: {e}")
        raise e

    @bagelbot.event
    async def on_command_error(ctx, e):
        # todo: stick this in a cog somehow
        await bot_common.on_command_error(bagelbot, ctx, e)

    @bagelbot.event
    async def on_command(ctx):
        msg = ctx.message
        log.info(f"{msg.guild}, {msg.channel}, {msg.author}: {msg.content}")

    bagelbot.add_cog(Voice(bagelbot))
    bagelbot.add_cog(Announcer(bagelbot))
    bagelbot.run(get_param("DISCORD_TOKEN"))



if __name__ == "__main__":
    main()

