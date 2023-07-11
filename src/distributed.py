
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


log = logging.getLogger("distributed")
log.setLevel(logging.DEBUG)


EVERYONE_WILDCARD = "#everyone"
ANYONE_WILDCARD = "#anyone"
DISCOVERY_ENDPOINT = "/ping"


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


async def endpoint_ping(node, **args):
    return {
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "instance": node.instance_uuid,
        "endpoints": list(node.endpoints.keys())
    }


async def endpoint_add(node, **args):
    return {"result": args["x"] + args["y"] + args["z"]}


async def endpoint_camera(node, **args):
    return {"result": "OK"}


def should_respond(caller_id, packet: Packet):
    if packet.src == caller_id:
        return False
    if packet.backlink:
        return False
    return packet.dst == caller_id or \
           packet.dst == ANYONE_WILDCARD or \
           packet.dst == EVERYONE_WILDCARD


class NetworkNode(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.comms_channel = None
        self.endpoints = {}
        self.instance_uuid = str(uuid.uuid4())
        self.caller_id = self.instance_uuid[:8]
        self.packet_buffer = collections.deque()


    async def send_packet(self, packet):
        log.info(f"SEND: {packet}")
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

        packets = await self.call_endpoint(ANYONE_WILDCARD, DISCOVERY_ENDPOINT, 100)
        for packet in packets:
            print(packet.src, packet.body)


    @commands.Cog.listener()
    async def on_message(self, message):

        if message.channel != self.comms_channel:
           return

        p = cast_to_packet(message.content)

        if not p:
            return

        now = datetime.now()
        self.packet_buffer.append((now, p))
        while self.packet_buffer[0][0] < now - timedelta(60)
            log.debug(f"Popping old packet: {self.packet_buffer[0][1]}")
            self.packet_buffer.popleft()

        if p.src != self.caller_id:
            log.info(f"RECV: {p}")

        if not should_respond(self.caller_id, p):
            return

        if not p.endpoint in self.endpoints:
            if p.dst != ANYONE_WILDCARD:
                resp = {
                    "error": f"Endpoint {p.endpoint} not valid for this node",
                    "error_type": "BadEndpoint"
                }
                q = make_response_packet(self.caller_id, p, **resp)
                await self.send_packet(q)
            return

        log.debug(f"Processing packet with endpoint {p.endpoint}")
        func = self.endpoints[p.endpoint]
        try:
            resp = await func(self, **p.body)
        except Exception as e:
            resp = {"error": f"{e}", "error_type": f"{type(e).__name__}"}
        q = make_response_packet(self.caller_id, p, **resp)
        await self.send_packet(q)

