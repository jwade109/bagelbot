#! /usr/bin/env python3

import os
import sys
import discord
import logging
from discord.ext import commands
from state_machine import get_param
from voice import Voice
import bagel_errors

log = logging.getLogger("cc")
log.setLevel(logging.DEBUG)
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
    format="[%(levelname)s] %(message)s")


class BagelHelper(commands.DefaultHelpCommand):

    async def send_pages(self):
        destination = self.get_destination()
        e = discord.Embed(color=discord.Color.blurple(),
            title="Help Text", description='')
        for page in self.paginator.pages:
            e.description += page
        await destination.send(embed=e)

    def __getattribute__(self, name):
        log.debug(f"getattr: {name}")
        return object.__getattribute__(self, name)


def main():

    intents = discord.Intents.default()
    intents.members = True
    intents.presences = True
    bagelbot = commands.Bot(command_prefix=["cc ", "CC ", "Cc ", "cC "],
        case_insensitive=True, intents=intents,
        help_command=BagelHelper())

    @bagelbot.event
    async def on_ready():
        log.info("Connected.")

    @bagelbot.event
    async def on_command_error(ctx, e):
        log.error(f"Error: {e}")
        await ctx.send(f"Error: {e}")
        raise e

    @bagelbot.event
    async def on_command_error(ctx, e):
        # todo: stick this in a cog somehow
        await bagel_errors.on_command_error(bagelbot, ctx, e)

    @bagelbot.event
    async def on_command(ctx):
        msg = ctx.message
        log.info(f"{msg.guild}, {msg.channel}, {msg.author}: {msg.content}")

    bagelbot.add_cog(Voice(bagelbot))
    bagelbot.run(get_param("DISCORD_TOKEN"))



if __name__ == "__main__":
    main()

