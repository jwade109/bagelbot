
import discord
import random
import giphy
import logging
from traceback import format_exception
from resource_paths import DUMB_FISH_PATH
from vernacular import enhance_sentence as SE


log = logging.getLogger("errors")
log.setLevel(logging.DEBUG)


class BagelHelper(discord.ext.commands.DefaultHelpCommand):
    pass

    # disabled for now -- issues with pagination, and exceeding
    # the maximum discord message size

    # async def send_pages(self):
    #     destination = self.get_destination()
    #     e = discord.Embed(color=discord.Color.blurple(),
    #         title="Help Text", description='')
    #     for page in self.paginator.pages:
    #         e.description += page
    #     await destination.send(embed=e)


async def report_error_occurred(bot, ctx, e):
    await ctx.send(f"Oof, ouch, my bones. Encountered an internal error. ({e})")
    await ctx.send(random.choice(giphy.search("error")), delete_after=30)
    msg = ctx.message
    errstr = format_exception(type(e), e, e.__traceback__)
    errstr = "\n".join(errstr)
    s = f"Error: {type(e).__name__}: {e}\n{errstr}\n"
    fmted = f"{msg.guild} {msg.channel} {msg.author} {msg.content}:\n{s}"
    log.error(fmted)
    bug_report_channel = bot.get_channel(908165358488289311)
    if not bug_report_channel:
        log.error("Failed to acquire handle to bug report channel!")
        return

    embed = discord.Embed(title="Error Report",
        description=f"Error of type {type(e).__name__} has occurred.",
        color=discord.Color.red())
    embed.add_field(name="Server", value=f"{msg.guild}", inline=True)
    embed.add_field(name="Channel", value=f"{msg.channel}", inline=True)
    embed.add_field(name="Author", value=f"{msg.author}", inline=True)
    embed.add_field(name="Message", value=f"{msg.content}", inline=False)
    embed.add_field(name="Full Exception", value=f"{e}", inline=False)
    file = discord.File(DUMB_FISH_PATH, filename="fish.png")
    embed.set_thumbnail(url="attachment://fish.png")
    await bug_report_channel.send(file=file, embed=embed)


async def on_command_error(bot, ctx, e):
    log.error(f"Error occurred: {ctx.author} invoked {ctx.invoked_with}, AKA {ctx.command}, causing {str(e)}")
    if type(e) is discord.ext.commands.errors.CommandNotFound:
        await ctx.send(SE("(($HEY)), ((THATS_NOT)) a command. (($DONT_KNOW_WHAT_UR_ON_ABOUT))"))
        await ctx.send(random.choice(giphy.search("confused")), delete_after=30)
        return
    if type(e) is discord.ext.commands.errors.CheckFailure:
        await ctx.send(SE("(($HEY)), you don't have sufficient permissions to use that command."))
        await ctx.send(random.choice(giphy.search("denied")), delete_after=30)
        return
    if type(e) is discord.ext.commands.errors.BadArgument:
        await ctx.send(SE("(($APOLOGY)), you've provided bad arguments for that command."))
        await ctx.send(random.choice(giphy.search("bad")), delete_after=30)
        return
    if type(e) is discord.ext.commands.errors.MissingRequiredArgument:
        log.debug(f"Invoked with: {ctx.invoked_with}, AKA {ctx.command}")
        await ctx.send(SE(f"You're missing a required argument for **{ctx.command}**. " \
            f"You can access the docs for it with:\n```\nbb help {ctx.command}\n```"))
        return
    await report_error_occurred(bot, ctx, e)


# get a rough estimate of where the host computer is located
def request_location(on_failure=[37, -81]):
    try:
        log.info("Requesting location from remote...")
        response = requests.get("http://ipinfo.io/json")
        data = response.json()
        loc = [float(x) for x in data['loc'].split(",")]
        log.info(f"Got {loc}.")
    except Exception as e:
        log.error(f"Failed to get location: {type(e)}, {e}")
        return on_failure
    return loc
