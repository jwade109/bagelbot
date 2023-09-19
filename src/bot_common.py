import os
import sys
import discord
import random
import giphy
import logging
from traceback import format_exception
from vernacular import enhance_sentence as SE
import requests
from bblog import log
from state_machine import load_yaml, get_param
from discord.ext import commands
import importlib


LOGGING_CHANNEL_ID = 908161498591928383
ALERTS_CHANNEL_ID = 908165358488289311
NODE_COMMS_CHANNEL_ID = 1128171384422551656
DONT_ALERT_USERS = discord.AllowedMentions(users=False)


async def report_error_occurred(bot, ctx, e):
    await ctx.send(f"Oof, ouch, my bones. Encountered an internal error. ({e})")
    await ctx.send(random.choice(giphy.search("error")), delete_after=30)
    msg = ctx.message
    errstr = format_exception(type(e), e, e.__traceback__)
    errstr = "\n".join(errstr)
    s = f"Error: {type(e).__name__}: {e}\n{errstr}\n"
    fmted = f"{msg.guild} {msg.channel} {msg.author} {msg.content}:\n{s}"
    log.error(fmted)
    bug_report_channel = bot.get_channel(ALERTS_CHANNEL_ID)
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
    await bug_report_channel.send(embed=embed)


async def on_error(bot, ctx, e):
    log.error(f"Error occurred: {ctx.author} invoked {ctx.invoked_with}, AKA {ctx.command}, causing {str(e)}")
    if type(e) is commands.errors.CommandNotFound:
        await ctx.send(SE("(($HEY)), ((THATS_NOT)) a command. (($DONT_KNOW_WHAT_UR_ON_ABOUT))"))
        await ctx.send(random.choice(giphy.search("confused")), delete_after=30)
        return
    if type(e) is commands.errors.CheckFailure:
        await ctx.send(SE("(($HEY)), you don't have sufficient permissions to use that command."))
        await ctx.send(random.choice(giphy.search("denied")), delete_after=30)
        return
    if type(e) is commands.errors.BadArgument:
        await ctx.send(SE("(($APOLOGY)), you've provided bad arguments for that command."))
        await ctx.send(random.choice(giphy.search("bad")), delete_after=30)
        return
    if type(e) is commands.errors.MissingRequiredArgument:
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


def import_class(module, classname):
    mod = importlib.import_module(module)
    cl = getattr(mod, classname)
    return cl


async def deploy_with_config(args):

    log.info(f"Configuring according to {args.config}")
    config = load_yaml(args.config, False)

    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix=config["prefixes"],
        case_insensitive=True, intents=intents)

    for cog_decl in config["cogs"]:
        name = cog_decl["name"]
        args = cog_decl.get("args", {})
        module, cogname = name.split("/")
        cog = import_class(f"plugins.{module}", cogname)
        if args:
            log.info(f"Including plugin {name} with args {args}")
            await bot.add_cog(cog(bot, **args))
        else:
            log.info(f"Including plugin {name}")
            await bot.add_cog(cog(bot))
    identity = config.get("identity", "")
    log.info(f"Deploying with identity token {identity}")

    @bot.event
    async def on_ready():
        log.info("Deployed.")

    @bot.event
    async def on_command_error(ctx, e):
        await on_error(bot, ctx, e)

    await bot.start(get_param(identity))

