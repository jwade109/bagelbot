#! /usr/bin/env python3

import os
import sys
import discord
import logging
from discord.ext import commands
from state_machine import get_param
import bot_common
from ws_dir import WORKSPACE_DIRECTORY
from datetime import datetime
import urllib.parse
import requests

from unprompted import Unprompted


DUDEBOT_ID = 934972571647090710
BOT_TEST_CHANNEL_ID = 807450116293132338


log = logging.getLogger("cc")
log.setLevel(logging.DEBUG)
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
    format="[%(levelname)s] [%(name)s] %(message)s")


async def send_message_to_dudebot(bot, msg):
    channel = await bot.fetch_channel(BOT_TEST_CHANNEL_ID)
    await channel.send(f"<@{DUDEBOT_ID}> {msg}")


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
        # channel = await bagelbot.fetch_channel(BOT_TEST_CHANNEL_ID)
        # await send_message_to_dudebot(bagelbot, "testicles")

    @bagelbot.event
    async def on_command_error(ctx, e):
        log.error(f"Error: {e}")
        await ctx.send(f"Error: {e}")
        raise e

    # @bagelbot.event
    # async def on_command_error(ctx, e):
    #     # todo: stick this in a cog somehow
    #     await bot_common.on_command_error(bagelbot, ctx, e)

    @bagelbot.event
    async def on_command(ctx):
        msg = ctx.message
        log.info(f"{msg.guild}, {msg.channel}, {msg.author}: {msg.content}")

    bagelbot.add_cog(Unprompted(bagelbot))

    bagelbot.run(get_param("CHOO_CHOO_DISCORD_TOKEN"))



if __name__ == "__main__":
    main()
