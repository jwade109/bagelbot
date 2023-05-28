#! /usr/bin/env python3

import sys
import discord
from discord.ext import commands
import logging
from resource_paths import tmp_fn
from typing import List
from dataclasses import dataclass
import yaml
from state_machine import get_param, set_param
from resource_paths import MLE_YAML



log = logging.getLogger("wikidump")
log.setLevel(logging.DEBUG)


SEPARATOR = "====================="


@dataclass()
class Message:
    pinned: bool = False
    attachments: List = None
    body: str = ""


def split_file_into_messages(filename) -> List:
    file = open(filename, 'r', encoding='utf-8-sig')
    if not file:
        return None

    contents = file.read()
    nodes = yaml.load(contents)

    ret = []
    for node in nodes:

        m = Message()
        m.pinned = node["pinned"] if "pinned" in node else False
        m.attachments = node["attachments"] if "attachments" in node else []
        m.body = node["body"]
        ret.append(m)
    return ret


class WikiDumper(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def whitelist(self, ctx, channel: discord.TextChannel):
        whitelist = get_param("channel_whitelist", set(), MLE_YAML)
        if channel.id in whitelist:
            await ctx.send(f"{channel.mention} is already whitelisted.")
            return
        whitelist.add(channel.id)
        set_param("channel_whitelist", whitelist, MLE_YAML)
        await ctx.send(f"{channel.mention} has been whitelisted.")


    @commands.command()
    async def blacklist(self, ctx, channel: discord.TextChannel):
        whitelist = get_param("channel_whitelist", set(), MLE_YAML)
        if not channel.id in whitelist:
            await ctx.send(f"{channel.mention} is already blacklisted.")
            return
        whitelist.remove(channel.id)
        set_param("channel_whitelist", whitelist, MLE_YAML)
        await ctx.send(f"{channel.mention} has been blacklisted.")


    @commands.command()
    async def write(self, ctx, channel: discord.TextChannel):
        whitelist = get_param("channel_whitelist", set(), MLE_YAML)
        if not channel.id in whitelist:
            await ctx.send(f"{channel.mention} is not whitelisted for wikidumping.")
            return

        if len(ctx.message.attachments) != 1:
            await ctx.send("Please provide exactly one text file to write.")
            return

        await channel.purge()

        log.info(f"Writing to {channel}")

        att = ctx.message.attachments[0]
        filename = tmp_fn("script", "txt")
        log.info(f"Saving attachment to {filename}")
        await att.save(filename)

        tokens = split_file_into_messages(filename)

        to_pin = []

        for t in tokens:
            m = await channel.send(t.body)
            if t.pinned:
                to_pin.append(m)

        for m in reversed(to_pin):
            await m.pin()


def main():

    print(sys.argv)
    print(yaml.load(open(sys.argv[1]).read()))



if __name__ == "__main__":
    main()

