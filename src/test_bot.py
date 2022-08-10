#! /usr/bin/env python3

import os
import sys
import discord
import logging
from discord.ext import commands
from state_machine import get_param
from voice import Voice
from othello import Othello
import bagel_errors
from help_formatting import BagelHelper
from ws_dir import WORKSPACE_DIRECTORY


YAML_PATH = WORKSPACE_DIRECTORY + "/private/announcements.yaml"


log = logging.getLogger("cc")
log.setLevel(logging.DEBUG)
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
    format="[%(levelname)s] %(message)s")


def determine_best_broadcast_channel(guild):
    bb_channel = get_param(f"{guild.id}/announce-channel", "bagel-announcements", YAML_PATH)
    enabled = get_param(f"{guild.id}/enable", True, YAML_PATH)
    text_channels = [c for c in guild.channels if c.type is discord.ChannelType.text]
    bb_channels = [c for c in text_channels if c.name.lower() == bb_channel]
    if bb_channels:
        log.info("Broadcast channel found!")
        return bb_channels[0]
    bagel_channels = [c for c in text_channels if "bagel" in c.name.lower()]
    if bagel_channels:
        log.info(f"{[str(c) for c in bagel_channels]}")
        return bagel_channels[0]
    max_users = max([len(c.members) for c in text_channels])
    best_channels = [c for c in text_channels if len(c.members) == max_users]
    if len(best_channels) == 1:
        return best_channels[0]
    general_channels = [c for c in best_channels if "general" in c.name.lower()]
    if not general_channels:
        best_channels = sorted(best_channels, key=lambda c: c.position)
        return best_channels[0]
    return general_channels[0]


def main():

    intents = discord.Intents.default()
    intents.members = True
    intents.presences = True
    bagelbot = commands.Bot(command_prefix=["cc ", "CC ", "Cc ", "cC "],
        case_insensitive=True, intents=intents,
        help_command=BagelHelper())

    @bagelbot.event
    async def on_ready():
        members = set()
        for guild in bagelbot.guilds:
            print(guild)
            for channel in [c for c in guild.channels if \
                c.type is discord.ChannelType.category]:
                print(f"- {channel}")
                for c in sorted(channel.channels, key=lambda c: c.position):
                    prefix = "#" if c.type is discord.ChannelType.text else "*"
                    print(f"-- {prefix}{c} ({len(c.members)}/{len(guild.members)})")
                    members |= set(c.members)

        log.info(f"Connected to {len(bagelbot.guilds)} servers with {len(members)} unique users.")
        for guild in bagelbot.guilds:
            log.info(f"{guild} ({len(guild.members)} users)")

        for guild in bagelbot.guilds:
            brc = determine_best_broadcast_channel(guild)
            log.info(f"{guild}: {brc} ({len(brc.members)}/{len(guild.members)})")


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

