import discord
from discord.ext import commands, tasks
from predicates import *
from resource_paths import *
from state_machine import get_param, set_param
from bblog import log, LOG_FILENAME, ARCHIVE_FILENAME
import bot_common
import shutil
import randomname
import random


class Debug(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.force_dump = False
        self.last_dump = None
        self.invoked_commands = []

    @commands.Cog.listener()
    async def on_command(self, ctx):
        msg = ctx.message
        s = f"{msg.guild} - {msg.channel} - {msg.author} - {msg.content}"
        log.debug(s)
        self.invoked_commands.append(s)

    @commands.Cog.listener()
    async def on_ready(self):
        self.log_dumper_checked.start()
        log.debug("Started log dump loop.")

    @tasks.loop(seconds=5)
    async def log_dumper_checked(self):
        try:
            await self.log_dumper()
        except Exception as e:
            log.error(f"Log dumper error: {e}")

    # update loop which dumps the daily logfile (log.txt) to the
    # discord server logging channel, as well as appends the daily
    # file to the archive log. clears the daily log once complete.
    # additionally, a user can force an off-schedule dump by setting
    # self.force_dump to True
    async def log_dumper(self):

        if not self.last_dump:
            self.last_dump = datetime.now()
            return
        now = datetime.now()

        next_dump = self.last_dump.replace( \
            hour=11, minute=0, second=0, microsecond=0)
        dump_logs_now = self.force_dump

        if dump_logs_now:
            log.info("Dumping logs off schedule by user request.")

        if now >= next_dump and self.last_dump <= next_dump:
            log.info(f"Scheduled log dump at {next_dump} triggered now.")
            dump_logs_now = True

        self.last_dump = now
        if not dump_logs_now:
            return

        man_auto = "Manual" if self.force_dump else "Automatic"
        self.force_dump = False

        if not os.path.exists(LOG_FILENAME) or os.stat(LOG_FILENAME).st_size == 0:
            log.info("No logs emitted in the previous period.")

        log_channel = self.bot.get_channel(bot_common.LOGGING_CHANNEL_ID)
        if not log_channel:
            log.warn("Failed to acquire handle to log dump channel. Retrying in 120 seconds...")
            await asyncio.sleep(120)
            log_channel = self.bot.get_channel(bot_common.LOGGING_CHANNEL_ID)
            if not log_channel:
                log.error("Failed to acquire handle to log dump channel!")
                return

        log.debug("Dumping.")

        try:
            if self.invoked_commands:
                embed = discord.Embed(title="Recent Activity",
                    description="\n".join(self.invoked_commands))
                await log_channel.send(embed=embed)
                self.invoked_commands = []
        except Exception as e:
            log.error(f"Failed to emit commands history readout: {e}")

        discord_fn = os.path.basename(tmp_fn("LOG", "txt"))
        await log_channel.send(f"Log dump {datetime.now()} ({man_auto})",
            file=discord.File(LOG_FILENAME, filename=discord_fn))

        arcfile = open(ARCHIVE_FILENAME, 'a')
        logfile = open(LOG_FILENAME, 'r')
        for line in logfile.readlines():
            arcfile.write(line)
        logfile.close()
        arcfile.close()
        open(LOG_FILENAME, 'w').close()

    @commands.command(help="Download the source code for this bot.")
    async def source(self, ctx):
        url = "https://github.com/jwade109/bagelbot"
        await ctx.send(url, file=discord.File(__file__))

    @commands.command(help="Get an invite link for this bot.")
    async def invite(self, ctx):
        link = "https://discord.com/oauth2/authorize?client_id=421167204633935901&permissions=378061188160&scope=bot"
        await ctx.send(link)

    # sets force_dump to True, so the log dumper loop will
    # see this on its next run and dump the daily log
    # off-schedule. only wade can run this command
    @commands.command(help="Manually upload logs before the next scheduled dump.")
    @wade_only()
    async def dump_logs(self, ctx):
        log.info("User requested manual log dump.")
        await ctx.send("Ok, logs will be uploaded soon.")
        self.force_dump = True

    @commands.command(name="good-bot", help="Tell BagelBot it's doing a good job.")
    async def good_bot(self, ctx):
        reports = get_param("kudos", 0)
        set_param("kudos", reports + 1)
        await ctx.send("Thanks.")

    @commands.command(name="bad-bot", help="Tell BagelBot it sucks.")
    async def bad_bot(self, ctx):
        reports = get_param("reports", 0)
        set_param("reports", reports + 1)
        await ctx.send("Wanker.")

    @commands.command(help="Check Raspberry Pi SD card utilization.")
    async def memory(self, ctx):
        total, used, free = shutil.disk_usage("/")
        await ctx.send(f"{used/2**30:0.3f} GB used; {free/2**30:0.3f} GB free ({used/total*100:0.1f}%)")

    # I feel I should note that I essentially never throw
    # exceptions in my actual programs because they are a truly
    # terrible way to handle off-nominal conditions. but other
    # people throw them all the time, so this tests the bot's
    # ability to handle unforeseen circumstances
    @commands.command(help="Throw an error for testing.")
    @wade_only()
    async def error(self, ctx):
        raise Exception("This is a fake error for testing.")

    # obviously, only wade should be able to run this
    @commands.command(help="Test for limited permissions.")
    @wade_only()
    async def only_wade(self, ctx):
        await ctx.send("Wanker.")

    @commands.command(help="Test for permissions for the nuclear codes.")
    @wade_or_collinses_only()
    async def only_collinses(self, ctx):
        await ctx.send("Tactical nuke incoming.")

    # bug report command. allows users to report bugs, with the
    # option to include a screen capture of the issue.
    # copies the report locally on the filesystem, and
    # forwards the report to a designated bug report channel
    # on the development server
    @commands.command(name="report-bug", aliases=["bug", "bug-report"], help="Use this to report bugs with BagelBot.")
    async def report_bug(self, ctx, *description):
        msg = ctx.message
        if not description:
            await ctx.send("Please include a written description of the bug. "
                "(Attached screenshots are also a big help for debugging!)")
            return
        description = " ".join(description)
        log.debug(f"Bug report description: '{description}'.")

        # generates a memorable-yet-random bug ticket name, something like electron-pug-892
        def get_bug_ticket_name():
            return randomname.get_name(adj=('physics'), noun=('dogs')) + \
                "-" + str(random.randint(100, 1000))

        ticket_name = get_bug_ticket_name()

        now = datetime.now()
        bug_dir = BUG_REPORT_DIR + "/" + ticket_name
        while os.path.exists(bug_dir):
            ticket_name = get_bug_ticket_name()
            bug_dir = BUG_REPORT_DIR + "/" + ticket_name
        os.mkdir(bug_dir)
        info_fn = bug_dir + "/report_info.txt"
        info_file = open(info_fn, "w")
        info_file.write(f"Description: {description}\n")
        info_file.write(f"Guild: {msg.guild}\n")
        info_file.write(f"Author: {msg.author}\n")
        info_file.write(f"Channel: {msg.channel}\n")
        info_file.write(f"Time: {now}\n")
        info_file.close()

        await ctx.send(f"Thanks for submitting a bug report. Your ticket is: {ticket_name}")

        dl_filename = None
        if msg.attachments:
            log.debug(f"Bug report directory: {bug_dir}")
            for att in msg.attachments:
                dl_filename = bug_dir + "/" + att.filename.lower()
                if any(dl_filename.endswith(image) for image in ["png", "jpeg", "gif", "jpg"]):
                    log.debug(f"Saving image attachment to {dl_filename}")
                    await att.save(dl_filename)
                else:
                    log.warn(f"Not saving attachment of unsupported type: {dl_filename}.")
                    dl_filename = None

        bug_report_channel = self.bot.get_channel(bot_common.ALERTS_CHANNEL_ID)
        if not bug_report_channel:
            log.error("Failed to acquire handle to bug report channel!")
            return
        discord_msg = f"```\n" + \
            f"Ticket name: {ticket_name}\n" + \
            f"Description: {description}\n" + \
            f"Guild:       {msg.guild}\n" + \
            f"Author:      {msg.author}\n" + \
            f"Channel:     {msg.channel}\n" + \
            f"Time:        {now}\n```"
        if dl_filename:
            await bug_report_channel.send(discord_msg, file=discord.File(dl_filename))
        else:
            await bug_report_channel.send(discord_msg)

