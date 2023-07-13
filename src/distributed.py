
import os
import socket
import uuid
from datetime import datetime, timedelta
from bot_common import NODE_COMMS_CHANNEL_ID
from enum import Enum
from dataclasses import dataclass, field, asdict
import json
import logging
import discord
from discord.ext import commands, tasks
import collections
import asyncio

# todo don't put this here?
import giphy
import random


log = logging.getLogger("distributed")
log.setLevel(logging.DEBUG)


EVERYONE_WILDCARD = "#everyone"
ANYONE_WILDCARD = "#anyone"
DISCOVERY_ENDPOINT = "/ping"
NODE_COG_NAME = "Node"


@dataclass()
class Packet:
    id: str = ""
    src: str = ""
    dst: str = ""
    endpoint: str = ""
    body: dict = field(default_factory=dict)
    backlink: str = ""


def make_packet(caller_id, dst, endpoint, **body):
    p = Packet()
    p.body = body
    p.endpoint = endpoint
    p.src = caller_id
    p.dst = dst
    p.id = str(uuid.uuid4())
    return p


def make_response_packet(caller_id, inp: Packet, **body):
    p = Packet()
    p.body = body
    p.endpoint = inp.endpoint
    p.src = caller_id
    p.dst = inp.src
    p.id = str(uuid.uuid4())
    p.backlink = inp.id
    return p


def cast_to_packet(text: str):
    try:
        d = json.loads(text)
        return Packet(**d)
    except Exception as e:
        return None


def get_cog_or_throw(bot, cog_name):
    cog = bot.get_cog(cog_name)
    if not cog:
        raise Exception(f"Cog {cog_name} not available")
    return cog


def bad_endpoint_body(caller_id, ep):
    return {
        "error": f"Endpoint {ep} not supported by node {caller_id}",
        "error_type": "BadEndpoint"
    }


async def endpoint_ping(bot, **args):
    """
    args: none
    returns: node information
    """
    node_iface = get_cog_or_throw(bot, NODE_COG_NAME)
    return {
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "instance": node_iface.instance_uuid,
        "endpoints": list(node_iface.endpoints.keys())
    }


async def endpoint_add(bot, **args):
    """
    args: x, y, z
    returns: x + y + z
    """
    return {"result": float(args["x"]) + float(args["y"]) + float(args["z"])}


async def endpoint_camera(bot, **args):
    """
    args: none
    returns: result=OK
    """
    return {"result": "OK"}


async def endpoint_ep_info(bot, **args):
    """
    args: endpoint
    returns: endpoint info
    """
    node_iface = get_cog_or_throw(bot, NODE_COG_NAME)
    ep = args["name"]
    if ep not in node_iface.endpoints:
        return bad_endpoint_body(node_iface.caller_id, ep)
    func = node_iface.endpoints[ep]
    doc = func.__doc__
    doclines = [l.strip() for l in doc.split("\n") if l.strip()] if doc else []
    return {"endpoint": ep, "funcname": func.__name__, "doc": doclines}


async def endpoint_giphy(bot, **args):
    """
    args: search
    returns: giphy URL
    """
    url = random.choice(giphy.search(args["search"]))
    return {"url": url}


def should_respond(caller_id, packet: Packet):
    if packet.src == caller_id:
        return False
    if packet.backlink:
        return False
    return packet.dst == caller_id or \
           packet.dst == ANYONE_WILDCARD or \
           packet.dst == EVERYONE_WILDCARD



def packet_to_embed(p):

    c = discord.Color.blue()
    if "error" in p.body:
        c = discord.Color.red()
    embed = discord.Embed(title=f"[{p.endpoint.upper()}] {p.src} -> {p.dst}", color=c)
    for k, v in p.body.items():
        embed.add_field(name=str(k), value=str(v))
    footer = f"{p.id}"
    if p.backlink:
        footer += f"\n{p.backlink}"
    embed.set_footer(text=footer)
    return embed


class Node(commands.Cog):

    def __init__(self, bot, caller_id=None):
        self.bot = bot
        self.comms_channel = None
        self.endpoints = {}
        self.instance_uuid = str(uuid.uuid4())
        self.caller_id = caller_id if caller_id else self.instance_uuid[:8]
        self.packet_buffer = collections.deque()

        self.register_endpoint("/ping",     endpoint_ping)
        self.register_endpoint("/add",      endpoint_add)
        self.register_endpoint("/endpoint", endpoint_ep_info)
        self.register_endpoint("/giphy",    endpoint_giphy)


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
        if dst == EVERYONE_WILDCARD or dst == ANYONE_WILDCARD:
            wait_for_n = 100

        await ctx.send(f"Calling {endpoint} on {dst} with args {body}...")
        packets = await self.call_endpoint(dst, endpoint, wait_for_n, **body)
        for p in packets:
            e = packet_to_embed(p)
            await ctx.send(embed=e)


    async def send_packet(self, packet):
        # log.info(f"SEND: {packet}")
        await self.comms_channel.send(json.dumps(asdict(packet)))


    async def send_and_await_responses(self, packet, wait_for_n=1):
        pid = packet.id
        await self.send_packet(packet)
        start = datetime.now()
        timeout = timedelta(seconds=2)
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
        p = make_packet(self.caller_id, dst, endpoint, **body)
        return await self.send_and_await_responses(p, wait_for_n)


    def register_endpoint(self, name, func):
        log.debug(f"Registering endpoint {name}")
        self.endpoints[name] = func


    @commands.Cog.listener()
    async def on_ready(self):
        self.comms_channel = self.bot.get_channel(NODE_COMMS_CHANNEL_ID)
        log.info("Logged into node communications channel #" \
            f"{self.comms_channel} as {self.caller_id}")


    @commands.Cog.listener()
    async def on_message(self, message):

        if message.channel != self.comms_channel:
           return

        p = cast_to_packet(message.content)

        if not p:
            return

        now = datetime.now()
        self.packet_buffer.append((now, p))
        while self.packet_buffer[0][0] < now - timedelta(60):
            log.debug(f"Popping old packet: {self.packet_buffer[0][1]}")
            self.packet_buffer.popleft()

        # if p.src != self.caller_id:
        #     log.info(f"RECV: {p}")

        if not should_respond(self.caller_id, p):
            return

        if not p.endpoint in self.endpoints:
            if p.dst != ANYONE_WILDCARD:
                resp = bad_endpoint_body(self.caller_id, p.endpoint)
                q = make_response_packet(self.caller_id, p, **resp)
                await self.send_packet(q)
            return

        log.debug(f"[{p.endpoint}] [{p.src} -> {p.dst}]")
        func = self.endpoints[p.endpoint]
        try:
            resp = await func(self.bot, **p.body)
        except Exception as e:
            resp = {"error": f"{e}", "error_type": f"{type(e).__name__}"}
        q = make_response_packet(self.caller_id, p, **resp)
        await self.send_packet(q)

