import discord
from discord.ext import commands
from bblog import log
from plugins.distributed import register_endpoint
import socket


class ServerRegister(commands.Cog):

    def __init__(self, bot, **kwargs):
        self.bot = bot
        self.server_name = kwargs.get("server_name", "0.0.0.0")
        self.server_address = kwargs.get("server_addr", "0.0.0.0")
        async def mc_callback(node_iface, **kwargs):
            return dict(
                running=True,
                hostname=socket.gethostname(),
                name=self.server_name,
                address=self.server_address
            )
        register_endpoint(bot, "/minecraft", mc_callback)
