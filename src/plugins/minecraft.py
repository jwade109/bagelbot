import discord
from discord.ext import commands
from bblog import log
import plugins.distributed as distributed
import socket


class Minecraft(commands.Cog):

    def __init__(self, bot, **kwargs):
        self.bot = bot
        self.server_node_name = kwargs["server_node_name"]


    @commands.command(name="server-status", aliases=["mcstat"])
    async def server_status(self, ctx):
        node_iface = distributed.get_cog_or_throw(self.bot, distributed.NODE_COG_NAME)
        packets = await node_iface.call_endpoint(self.server_node_name, "/minecraft", 1)
        if not packets:
            await ctx.send("The server is not up.")
            return
        p = packets[0]
        if "error" in p.body:
            await ctx.send("The server is not up.")
            return
        await ctx.send("The server is up!", embed=distributed.packet_to_embed(p))


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
        distributed.register_endpoint(bot, "/minecraft", mc_callback)
