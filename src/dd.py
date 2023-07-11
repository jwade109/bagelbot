#! /usr/bin/env python3

import sys
import asyncio
import discord
import logging
from discord.ext import commands
from state_machine import get_param
import bot_common
from resource_paths import TEST_CONFIG
import distributed


print(sys.version)
print(sys.version_info)


log = logging.getLogger("cc")
log.setLevel(logging.DEBUG)
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
    format="[%(levelname)s] [%(name)s] %(message)s")


intents = discord.Intents.all()
cc = commands.Bot(command_prefix=["cc ", "CC ", "Cc ", "cC "],
    case_insensitive=True, intents=intents)


@cc.event
async def on_ready():
    log.info(f"Connected.")


async def main():

    distributed.CALLER_ID = "dd"
    if len(sys.argv) > 1:
        distributed.CALLER_ID = sys.argv[1]

    await bot_common.deploy_with_config(cc, TEST_CONFIG)
    await cc.start(get_param("DANIEL_DISCORD_TOKEN"))


asyncio.run(main())
