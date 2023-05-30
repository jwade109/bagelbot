#! /usr/bin/env python3

import sys
import os
import discord
import requests
from discord.ext import commands
import logging
from resource_paths import tmp_fn
from typing import List
from dataclasses import dataclass
import yaml
from state_machine import get_param, set_param
from resource_paths import MLE_YAML, MLE_SCRIPTS_DIR


# ghost librarians
ALYSSA_ID = 701567489552679002
WADE_ID = 235584665564610561


log = logging.getLogger("wikidump")
log.setLevel(logging.DEBUG)


SEPARATOR = "====================="
DONT_ALERT_USERS = discord.AllowedMentions(users=False)


def download_file(url, destination):
    log.info(f"Downloading file at {url} to {destination}.")
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) " \
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    response = requests.get(url, headers=headers)
    bin = response.content
    file = open(destination, "wb")
    if not file:
        log.error(f"Failed to open {destination}.")
        return
    file.write(bin)
    file.close()


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
        m.body = node["body"] if "body" in node else ""
        ret.append(m)
    return ret



def is_administrator(user_id):
    return user_id == ALYSSA_ID


class WikiDumper(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.whitelist = get_param("channel_whitelist", [], MLE_YAML)
        self.librarians = get_param("librarians", [], MLE_YAML)


    def write_whitelist(self):
        set_param("channel_whitelist", self.whitelist, MLE_YAML)


    def write_librarians(self):
        set_param("librarians", self.librarians, MLE_YAML)


    @commands.command()
    async def hire(self, ctx, user: discord.User):
        if not is_administrator(ctx.author.id):
            await ctx.send("You don't have permission to hire librarians.")
            return
        if user.id in self.librarians:
            await ctx.send(f"{user.mention} is already a librarian.",
                allowed_mentions=DONT_ALERT_USERS)
            return
        self.librarians.append(user.id)
        self.write_librarians()
        await ctx.send(f"{user.mention} has been hired as a librarian.",
            allowed_mentions=DONT_ALERT_USERS)


    @commands.command()
    async def fire(self, ctx, user: discord.User):
        if not is_administrator(ctx.author.id):
            await ctx.send("You don't have permission to fire librarians.")
            return
        if not user.id in self.librarians:
            await ctx.send(f"{user.mention} is not a librarian.",
                allowed_mentions=DONT_ALERT_USERS)
            return
        self.librarians.remove(user.id)
        self.write_librarians()
        await ctx.send(f"{user.mention} has been fired as a librarian.",
            allowed_mentions=DONT_ALERT_USERS)


    @commands.command()
    async def staff(self, ctx):
        if not self.librarians:
            await ctx.send("There are currently no librarians registered.")
            return
        text = "The following users are librarians:"
        for user_id in self.librarians:
            user = await self.bot.fetch_user(user_id)
            text += f"\n* {user.mention}"
        await ctx.send(text, allowed_mentions=DONT_ALERT_USERS)


    async def show_whitelist(self, ctx):
        if not self.whitelist:
            await ctx.send("No channels are currently whitelisted.")
            return
        text = "The following channels are whitelisted:"
        to_remove = set()
        for channel_id in self.whitelist:
            try:
                # this will fail if the channel has been deleted
                channel = await self.bot.fetch_channel(channel_id)
                log.debug(f"{channel_id} -> {channel.guild}/{channel}")
            except Exception as e:
                log.error(f"For channel {channel_id}, caught an error in fetch_channel: {e}")
                # remove channel from the whitelist
                to_remove.add(channel_id)
                continue
            text += f"\n* {channel.mention}"
        for trm in to_remove:
            self.whitelist.remove(trm)
        if to_remove:
            self.write_whitelist()
        await ctx.send(text)


    @commands.command()
    async def whitelist(self, ctx, channel: discord.TextChannel = None):
        if not channel:
            return await self.show_whitelist(ctx)
        if not is_administrator(ctx.author.id):
            await ctx.send("You don't have permission to modify the whitelist.")
            return
        if channel.id in self.whitelist:
            await ctx.send(f"{channel.mention} is already whitelisted.")
            return
        self.whitelist.append(channel.id)
        self.write_whitelist()
        await ctx.send(f"{channel.mention} has been whitelisted.")


    @commands.command()
    async def blacklist(self, ctx, channel: discord.TextChannel = None):
        if not channel:
            return await self.show_whitelist(ctx)
        if not is_administrator(ctx.author.id):
            await ctx.send("You don't have permission to modify the whitelist.")
            return
        if not channel.id in self.whitelist:
            await ctx.send(f"{channel.mention} is already blacklisted.")
            return
        self.whitelist.remove(channel.id)
        self.write_whitelist()
        await ctx.send(f"{channel.mention} has been blacklisted.")


    @commands.command()
    async def post(self, ctx, channel: discord.TextChannel, script_name: str = None):

        if not ctx.author.id in self.librarians:
            if is_administrator(ctx.author.id):
                await ctx.send(f"{ctx.author.mention} is an unlisted librarian.",
                    allowed_mentions=DONT_ALERT_USERS)
            else:
                await ctx.send(f"{ctx.author.mention} is not a librarian.",
                    allowed_mentions=DONT_ALERT_USERS)
                return

        if not channel.id in self.whitelist:
            await ctx.send(f"{channel.mention} is not whitelisted for wikidumping.")
            return

        if not script_name and len(ctx.message.attachments) != 1:
            await ctx.send("Please provide exactly one text file to write.")
            return

        await channel.purge()

        log.info(f"Posting to {channel}")

        if script_name:
            filename = os.path.join(MLE_SCRIPTS_DIR, script_name + ".yml")
            log.info(f"Posting from saved file {filename}")
        else:
            filename = tmp_fn("script", "txt")
            att = ctx.message.attachments[0]
            log.info(f"Saving attachment to {filename}")
            await att.save(filename)

        tokens = split_file_into_messages(filename)

        to_pin = []

        for i, t in enumerate(tokens):

            if not t.body and not t.attachments:
                await ctx.send(f"Warning: skipping element {i} with no body and no attachments.")
                continue

            files = []

            for url in t.attachments:
                fn = tmp_fn("attach", "jpg")
                download_file(url, fn)
                files.append(discord.File(fn))

            if t.body:
                m = await channel.send(t.body, files=files)
            else:
                m = await channel.send(files=files)
            if t.pinned:
                to_pin.append(m)

        for i, m in enumerate(reversed(to_pin)):
            k = await m.pin()
            if i + 1 != len(to_pin):
                last = await channel.fetch_message(channel.last_message_id)
                await last.delete()



def main():

    print(sys.argv)
    print(yaml.load(open(sys.argv[1]).read()))



if __name__ == "__main__":
    main()

