#! /usr/bin/env python3

print("Starting bagelbot test...")

import os
import sys
import discord
from discord.ext import commands
from state_machine import get_param
from remindme import RemindV2
from othello import Othello

def main():

    intents = discord.Intents.default()
    intents.members = True
    intents.presences = True
    bagelbot = commands.Bot(command_prefix=["cc "],
        case_insensitive=True, intents=intents)

    @bagelbot.event
    async def on_ready():
        print("Connected.")

    @bagelbot.event
    async def on_command_error(ctx, e):
        print(f"Error: {e}")

    @bagelbot.event
    async def on_command(ctx):
        msg = ctx.message
        print(f"{msg.guild}, {msg.channel}, {msg.author}: {msg.content}")

    bagelbot.add_cog(Othello(bagelbot))
    bagelbot.run(get_param("DISCORD_TOKEN"))



if __name__ == "__main__":
    main()

