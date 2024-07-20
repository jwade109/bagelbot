
from state_machine import get_param
from discord.ext import commands

import bagelshop.astronomy as astro


NASA_API_KEY = get_param("NASA_API_KEY", "")


class Astronomy(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def apod(self, ctx, when: str = ""):
        if when == "*":
            apod = astro.get_apod(NASA_API_KEY, None, True)
        else:
            dt = astro.str_to_datetime(when)
            if when and not dt:
                await ctx.send("Bad 'when' argument: Requires dates of the form YYYY-MM-DD.")
                return
            apod = astro.get_apod(NASA_API_KEY, dt)
        await ctx.send(embed=astro.apod_to_embed(apod))
