import discord
from discord.ext import commands
from state_machine import get_param

intents = discord.Intents.default()
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix=[], intents=intents)

@bot.event
async def on_ready():
    for guild in bot.guilds:
        print(guild)
        async for member in guild.fetch_members():
            nick = "" if member.name == member.display_name else member.display_name
            if nick:
                nick = f"(AKA {nick})"
            print(member.id, member, nick)

bot.run(get_param("DISCORD_TOKEN"))
