
import discord
import random
import giphy
import logging
from traceback import format_exception
from resource_paths import DUMB_FISH_PATH


log = logging.getLogger("errors")
log.setLevel(logging.DEBUG)


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
    if type(e) is discord.ext.commands.errors.CommandNotFound:
        await ctx.send("That's not a command; I don't know what you're on about.")
        await ctx.send(random.choice(giphy.search("confused")), delete_after=30)
        return
    if type(e) is discord.ext.commands.errors.CheckFailure:
        await ctx.send("Hey, you don't have sufficient permissions to use that command.")
        await ctx.send(random.choice(giphy.search("denied")), delete_after=30)
        return
    if type(e) is discord.ext.commands.errors.BadArgument:
        await ctx.send(f"Sorry, you've provided bad arguments for that command.")
        await ctx.send(random.choice(giphy.search("bad")), delete_after=30)
        return
    if type(e) is discord.ext.commands.errors.MissingRequiredArgument:
        log.debug(f"Invoked with: {ctx.invoked_with}, AKA {ctx.command}")
        await ctx.send(f"You're missing a required argument for **{ctx.command}**. " \
            f"You can access the docs for it with:\n```\nbb help {ctx.command}\n```")
        return
    await report_error_occurred(bot, ctx, e)