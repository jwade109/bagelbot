#! /usr/bin/env python3

import sys
import asyncio
import discord
import logging
from discord.ext import commands
from state_machine import get_param
import bot_common
import distributed
from bblog import log
import argparse


print(sys.version)
print(sys.version_info)


bot_name = sys.argv[1]


intents = discord.Intents.all()
cc = commands.Bot(command_prefix=[f"{bot_name} "],
    case_insensitive=True, intents=intents)


@cc.event
async def on_ready():
    log.info("Connected.")


async def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    args = parser.parse_args()

    await bot_common.deploy_with_config(cc, args.config)

    node_iface = cc.get_cog(distributed.NODE_COG_NAME)
    if node_iface:
        node_iface.caller_id = bot_name
        node_iface.register_endpoint("/camera",   distributed.endpoint_camera)

    await cc.start(get_param("DANIEL_DISCORD_TOKEN"))


asyncio.run(main())
