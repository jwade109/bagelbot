import socket
import uuid
from datetime import datetime, timedelta
from dataclasses import asdict
import json
import discord
from discord.ext import commands
import collections
import asyncio
import randomname

from bagelshop.logging import log
import bagelshop.distributed as bbdds

# TODO move back to bot_common?
NODE_COMMS_CHANNEL_ID = 1128171384422551656

class Node(commands.Cog):


    def __init__(self, bot, **kwargs):
        self.bot = bot
        self.comms_channel = None
        self.endpoints = {}
        self.instance_uuid = str(uuid.uuid4())
        self.caller_id = kwargs.get("callerid", randomname.get_name())
        self.packet_buffer = collections.deque()

        self.register_endpoint("/ping",     bbdds.endpoint_ping)
        self.register_endpoint("/add",      bbdds.endpoint_add)
        self.register_endpoint("/endpoint", bbdds.endpoint_ep_info)


    @commands.command()
    async def call(self, ctx, dst, endpoint, *args):

        body = {}
        for arg in args:
            try:
                k, v = arg.split("=")
            except Exception:
                continue
            body[k] = v

        wait_for_n = 1
        if dst == bbdds.EVERYONE_WILDCARD or dst == bbdds.ANYONE_WILDCARD:
            wait_for_n = 100


        sent = bbdds.make_packet(self.caller_id, dst, endpoint, **body)
        es = bbdds.packet_to_embed(sent)
        await ctx.send(f"Calling {endpoint} on {dst} with args {body}...", embed=es)
        packets = await self.send_and_await_responses(sent, wait_for_n)
        for p in packets:
            e = bbdds.packet_to_embed(p)
            await ctx.send(embed=e)
        if not packets:
            await ctx.send("No response.")


    async def send_packet(self, packet):
        # log.info(f"SEND: {packet}")
        await self.comms_channel.send(json.dumps(asdict(packet)))


    async def send_and_await_responses(self, packet, wait_for_n=1):
        pid = packet.id
        await self.send_packet(packet)
        start = datetime.now()
        timeout = timedelta(seconds=5) # TODO make this configurable
        dt = 0.1 # seconds
        grabbed = set()
        responses = []
        while len(responses) < wait_for_n and datetime.now() < start + timeout:
            for time, packet in self.packet_buffer:
                if packet.backlink == pid and packet.id not in grabbed:
                    responses.append(packet)
                    grabbed.add(packet.id)
            if len(responses) < wait_for_n:
                await asyncio.sleep(dt)
        return responses


    async def call_endpoint(self, dst, endpoint, wait_for_n, **body):
        p = bbdds.make_packet(self.caller_id, dst, endpoint, **body)
        return await self.send_and_await_responses(p, wait_for_n)


    def register_endpoint(self, name, func):
        log.debug(f"Registering endpoint {name}")
        self.endpoints[name] = func


    async def send_file(self, filename):
        m = await self.comms_channel.send(file=discord.File(filename))
        return m.attachments[0].url


    @commands.Cog.listener()
    async def on_ready(self):
        self.comms_channel = self.bot.get_channel(NODE_COMMS_CHANNEL_ID)
        log.info("Logged into node communications channel #" \
            f"{self.comms_channel} as \"{self.caller_id}\"")


    @commands.Cog.listener()
    async def on_message(self, message):

        if message.channel != self.comms_channel:
           return

        p = bbdds.cast_to_packet(message.content)

        if not p:
            return

        now = datetime.now()
        self.packet_buffer.append((now, p))
        while self.packet_buffer[0][0] < now - timedelta(60):
            log.debug(f"Popping old packet: {self.packet_buffer[0][1]}")
            self.packet_buffer.popleft()

        # if p.src != self.caller_id:
        #     log.info(f"RECV: {p}")

        if not bbdds.should_respond(self.caller_id, p):
            return

        if not p.endpoint in self.endpoints:
            if p.dst != bbdds.ANYONE_WILDCARD:
                resp = bbdds.bad_endpoint_body(self.caller_id, p.endpoint)
                q = bbdds.make_response_packet(self.caller_id, p, **resp)
                await self.send_packet(q)
            return

        log.debug(f"[{p.endpoint}] [{p.src} -> {p.dst}]")
        func = self.endpoints[p.endpoint]
        try:
            resp = await func(self, **p.body)
        except Exception as e:
            resp = {
                "error": f"{e}",
                "error_type": f"{type(e).__name__}",
                "hostname": socket.gethostname()
            }
        q = bbdds.make_response_packet(self.caller_id, p, **resp)
        await self.send_packet(q)

