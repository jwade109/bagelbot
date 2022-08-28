
import discord
from ws_dir import WORKSPACE_DIRECTORY
from state_machine import get_param, set_param
from ws_dir import WORKSPACE_DIRECTORY
import logging
from discord.ext import commands, tasks
from datetime import datetime
from gps_time import GPSTime
import requests
import random
from predicates import wade_only
import randomname as rn


YAML_PATH = WORKSPACE_DIRECTORY + "/private/announcements.yaml"


log = logging.getLogger("announcements")
log.setLevel(logging.DEBUG)


# enabled = get_param(f"{guild.id}/enable", False, YAML_PATH)
# if not enabled:
#     log.debug(f"{guild} hasn't enabled announcements.")
#     return None


def get_broadcast_channel(bot_member, guild):
    bb_channel = get_param(f"{guild.id}/announce-channel", 0, YAML_PATH)

    def filter_channel(c):
        if not c.type is discord.ChannelType.text:
            return False
        perms = c.permissions_for(bot_member)
        return perms.send_messages

    text_channels = [c for c in guild.channels if filter_channel(c)]
    bb_channels = [c for c in text_channels if c.id == bb_channel]
    if bb_channels:
        return bb_channels[0], True
    bagel_channels = [c for c in text_channels if "bagel" in c.name.lower()]
    if bagel_channels:
        log.info(f"{[str(c) for c in bagel_channels]}")
        return bagel_channels[0], False
    max_users = max([len(c.members) for c in text_channels])
    best_channels = [c for c in text_channels if len(c.members) == max_users]
    if len(best_channels) == 1:
        return best_channels[0], False
    general_channels = [c for c in best_channels if "general" in c.name.lower()]
    if not general_channels:
        best_channels = sorted(best_channels, key=lambda c: c.position)
        return best_channels[0], False
    return general_channels[0], False


async def make_announcement_if_enabled(bot_member, guild, message, embed, dry_run, message_undecideds):
    enabled = get_param(f"{guild.id}/enable", 1, YAML_PATH)
    if enabled == 0:
        log.info(f"{guild} has opted out of announcements.")
        return
    if enabled == 1 and not message_undecideds:
        log.info(f"{guild} has not opted in or out (message_undecideds={message_undecideds}); not announcing to them.")
        return
    best_channel, explicit = get_broadcast_channel(bot_member, guild)
    if not best_channel:
        log.error(f"Failed to get a broadcast channel for guild {guild}!")
        return False
    try:
        if dry_run:
            log.warn(f"Would have sent an announcement to {guild}/{best_channel}.")
        else:
            if embed:
                await best_channel.send(message, embed=embed)
            else:
                await best_channel.send(message)
    except Exception as e:
        log.error(f"Failed to broadcast to {guild}/#{best_channel}: {e}")
        return False

    log.info(f"Successfully announced to {guild}/#{best_channel} (dry_run = {dry_run}).")
    return True


def generate_announcement_embed(message):
    r1 = requests.get("http://api.open-notify.org/iss-now.json").json()
    r2 = requests.get("http://api.open-notify.org/astros.json").json()
    iss = r1["iss_position"]
    issloc = [float(iss[x]) for x in ["latitude", "longitude"]]
    people_in_space = r2["number"]
    person = random.choice(r2["people"])
    name = person["name"].upper().replace(" ", "~")

    gibberish = "".join(x.upper() for x in
        rn.sample_words("adjectives/physics", "3d_printing", n=1))
    space_facts = f"/{issloc[0]:0.5f}.{issloc[1]:0.5f}%//{name}[{people_in_space}]\\"
    lines = message.split("\n")
    gpst = GPSTime.from_datetime(datetime.now())
    title = f"🥯 📡 BROADCAST ALL//{gpst.week_number}@{gpst.time_of_week:0.3f}/"
    desc = f"```\n{message}\n```"
    embed = discord.Embed(title=title, description=desc)
    embed.add_field(name="METADATA", value=f"{space_facts}{gibberish}", inline=False)
    embed.set_footer(text="Use \"bb help Announcements\" for more info --\n" \
        "Direct message kim_mcbudget#4618 if things are broken or annoying")
    return embed


async def announce_to_all(bot, message, dry_run, message_undecideds):
    embed = generate_announcement_embed(message)
    for guild in bot.guilds:
        set_param(f"{guild.id}/name", guild.name, YAML_PATH)
        bot_member = await guild.fetch_member(bot.user.id)
        success = await make_announcement_if_enabled(bot_member, guild,
            "", embed, dry_run, message_undecideds)


async def get_reply_content(ctx):
    if not ctx.message.reference or not ctx.message.reference.message_id:
        return None
    uid = ctx.message.reference.message_id
    msg = await ctx.fetch_message(uid)
    return msg.content


class Announcements(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @wade_only()
    async def announce(self, ctx, dry_run: bool = True, message_undecideds = False):
        content = await get_reply_content(ctx)
        if not content:
            content = "This is a test announcement.\n\nThank you for your participation."
        s = f"Announcing; dry_run = {dry_run}, message_undecideds = {message_undecideds}."
        log.info(s)
        await ctx.send(s)
        if dry_run:
            embed = generate_announcement_embed(content)
            await ctx.send(embed=embed)
        await announce_to_all(self.bot, content, dry_run, message_undecideds)

    @commands.command(name="announce-optout")
    async def announce_optout(self, ctx):
        set_param(f"{ctx.guild.id}/enable", 0, YAML_PATH)
        await ctx.send("Opting out of announcements for this server.")

    @commands.command(name="announce-optin")
    async def enable_announcements(self, ctx):
        set_param(f"{ctx.guild.id}/enable", 2, YAML_PATH)
        await ctx.send("Opting in for announcements in this server.")

    @commands.command(name="announce-channel")
    async def set_announcement_channel(self, ctx, channel: discord.TextChannel):
        set_param(f"{ctx.guild.id}/announce-channel", channel.id, YAML_PATH)
        await ctx.send(f"Set this server's announcement channel to {channel.mention}.")
