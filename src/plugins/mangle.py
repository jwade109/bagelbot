import googletrans
import sys
import random

translator = googletrans.Translator()


def random_lang_code():
    return random.choice(list(googletrans.LANGUAGES.keys()))


def translate_back_and_forth(msg, n=50):
    src = "en"
    log.debug(f"Mangling: {msg}")
    for i in range(n):
        if i + 1 == n:
            dst = "en"
        else:
            dst = random_lang_code()
        if src == dst:
            continue
        res = translator.translate(msg, src=src, dest=dst)
        msg = res.text
        src = dst
    log.debug(f"Result: {msg}")
    return msg


def main():
    m = translate_back_and_forth(" ".join(sys.argv[1:]))
    print(f"\n{m}")


if __name__ == "__main__":
    main()
    exit()


import discord
from discord.ext import commands
from state_machine import get_param, set_param
from bagelshop.logging import log
from bot_common import get_reply_content


# https://github.com/ssut/py-googletrans
# https://readthedocs.org/projects/py-googletrans/downloads/pdf/latest/

class Mangle(commands.Cog):

    def __init__(self, bot, **args):
        self.bot = bot
        self.strength = args.get("strength", 50)

    @commands.command(help="Mangle a message")
    async def mangle(self, ctx, *message):

        last_msg_content = None

        channel = await self.bot.fetch_channel(ctx.message.channel.id)
        messages = [m.content async for m in channel.history(limit=6) if m.content]
        if len(messages) > 1:
            last_msg_content = messages[1]

        # channel = await self.bot.fetch_channel(ctx.message.channel.id)
        # if channel.last_message_id:
        #     last = await ctx.fetch_message(channel.last_message_id)
        #     last_msg_content = last.content if last else None
        reply_content = await get_reply_content(ctx)

        log.debug(f"Previous message: {last_msg_content}")
        log.debug(f"Reply to: {reply_content}")

        if not reply_content and not reply_content is None:
            await ctx.send("You've chosen a message to mangle, but it contains no text.")
            return

        to_mangle = ""

        if message:
            to_mangle = " ".join(message)
        elif reply_content:
            to_mangle = reply_content
        elif last_msg_content:
            to_mangle = last_msg_content
        else:
            await ctx.send("Please provide a message to mangle, or reply to a previous message.")
            return

        to_edit = await ctx.send(f"_Mangling \"{to_mangle}\" (n={self.strength})..._")
        mangled = translate_back_and_forth(to_mangle, self.strength)
        await to_edit.edit(content=mangled)

    # @commands.Cog.listener()
    # async def on_ready(self):
    #     self.update_ticker.start()
    #     log.debug("Started ticker loop.")

    # async def refresh(self):
    #     TICKER_NEXT_MSG_PERIOD = 60*5 # seconds

    #     if self.user_set_ticker is not None:
    #         time_set = self.user_set_ticker[1]
    #         age = datetime.now() - time_set
    #         if age > timedelta(seconds=TICKER_NEXT_MSG_PERIOD):
    #             log.debug(f"New message {self.user_set_ticker[0]} has expired.")
    #             self.user_set_ticker = None

    #     dt = timedelta(seconds=int(time.time() - psutil.boot_time()))

    #     activity = discord.ActivityType.playing

    #     msg = ""
    #     if self.user_set_ticker is not None:
    #         msg = self.user_set_ticker[0]
    #     else:
    #         msg = f"updog {dt}"
    #         i = int(dt.total_seconds() / TICKER_NEXT_MSG_PERIOD) % (len(self.ticker_lines) * 2 + 1)
    #         if i > 0:
    #             i -= 1
    #             msg = self.ticker_lines[i // 2]

    #     act = discord.Activity(type=activity, name=msg)
    #     await self.bot.change_presence(activity=act)

    # # run on a loop to update the bot status ticker
    # # loops through a list of statuses (which can be added to via
    # # the "bb status" command), visiting each one for a short time.
    # # appends "(at night)" to the status string if there are
    # # active SSH sessions (i.e. the bot is under maintenance)
    # @tasks.loop(seconds=30)
    # async def update_ticker(self):
    #     try:
    #         await self.refresh()
    #     except Exception as e:
    #         log.debug(f"Failed to change presence: {type(e)} {e}")

    # @commands.command(help="Add a status message to BagelBot.")
    # async def status(self, ctx, *message):
    #     if not message:
    #         await ctx.send("Please provide a status message for this command.")
    #         return
    #     message = " ".join(message)
    #     log.info(f"New ticker status: {message}")
    #     log.debug(f"{ctx.message.author} is adding a status: {message}")
    #     self.ticker_lines.append(message)
    #     set_param("ticker", self.ticker_lines)
    #     self.user_set_ticker = (message, datetime.now())
    #     await ctx.send(f"Thanks, your message \"{message}\" will be seen by literally several people.")
    #     await self.refresh()
