#! /usr/bin/env python3

import sys
import asyncio
import discord
import logging
from discord.ext import commands
from state_machine import get_param
from resource_paths import MLE_YAML

from wikidumping import WikiDumper


print(sys.version)
print(sys.version_info)


log = logging.getLogger("lib")
log.setLevel(logging.DEBUG)
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
    format="[%(levelname)s] [%(name)s] %(message)s")


intents = discord.Intents.all()
bot = commands.Bot(command_prefix=["!"],
    case_insensitive=True, intents=intents)


@bot.event
async def on_command_error(ctx, e):
    await ctx.send(f"Uh oh, there was an error ({type(e).__name__}): {e}")
    raise e


@bot.event
async def on_ready():
    log.info(f"Connected.")


async def main():
    await bot.add_cog(WikiDumper(bot))
    await bot.start(get_param("MLE_LIBRARIAN_API_TOKEN", None, MLE_YAML))


asyncio.run(main())
