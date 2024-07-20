#! /usr/bin/env python3

import gocomics

def main():

    for e in gocomics.search("calvin and hobbes"):
        print(f"{e.identifier}, {e.date}")

    exit()

if __name__ == "__main__":
    main()

from discord.ext import commands
from state_machine import get_param, set_param

class Subscriptions(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def calvin(self, ctx):
        await ctx.send("Hello")
