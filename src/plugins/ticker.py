import discord
from discord.ext import commands, tasks
from state_machine import get_param, set_param
from bagelshop.logging import log
from datetime import datetime, timedelta
import time
import psutil


class Ticker(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.user_set_ticker = None
        self.ticker_lines = get_param("ticker", [])

    @commands.Cog.listener()
    async def on_ready(self):
        self.update_ticker.start()
        log.debug("Started ticker loop.")

    async def refresh(self):
        TICKER_NEXT_MSG_PERIOD = 60*5 # seconds

        if self.user_set_ticker is not None:
            time_set = self.user_set_ticker[1]
            age = datetime.now() - time_set
            if age > timedelta(seconds=TICKER_NEXT_MSG_PERIOD):
                log.debug(f"New message {self.user_set_ticker[0]} has expired.")
                self.user_set_ticker = None

        dt = timedelta(seconds=int(time.time() - psutil.boot_time()))

        activity = discord.ActivityType.playing

        msg = ""
        if self.user_set_ticker is not None:
            msg = self.user_set_ticker[0]
        else:
            msg = f"updog {dt}"
            i = int(dt.total_seconds() / TICKER_NEXT_MSG_PERIOD) % (len(self.ticker_lines) * 2 + 1)
            if i > 0:
                i -= 1
                msg = self.ticker_lines[i // 2]

        act = discord.Activity(type=activity, name=msg)
        await self.bot.change_presence(activity=act)

    # run on a loop to update the bot status ticker
    # loops through a list of statuses (which can be added to via
    # the "bb status" command), visiting each one for a short time.
    # appends "(at night)" to the status string if there are
    # active SSH sessions (i.e. the bot is under maintenance)
    @tasks.loop(seconds=30)
    async def update_ticker(self):
        try:
            await self.refresh()
        except Exception as e:
            log.debug(f"Failed to change presence: {type(e)} {e}")

    @commands.command(help="Add a status message to BagelBot.")
    async def status(self, ctx, *message):
        if not message:
            await ctx.send("Please provide a status message for this command.")
            return
        message = " ".join(message)
        log.info(f"New ticker status: {message}")
        log.debug(f"{ctx.message.author} is adding a status: {message}")
        self.ticker_lines.append(message)
        set_param("ticker", self.ticker_lines)
        self.user_set_ticker = (message, datetime.now())
        await ctx.send(f"Thanks, your message \"{message}\" will be seen by literally several people.")
        await self.refresh()
