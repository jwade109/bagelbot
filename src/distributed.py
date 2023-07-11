
import os
import socket
import uuid
from datetime import datetime
from bot_common import NODE_COMMS_CHANNEL_ID
from enum import Enum
from dataclasses import dataclass, field, asdict
import json


INSTANCE_UUID = uuid.uuid4()

CALLER_ID = "anonymous-caller"
EVERYONE_WILDCARD = "#everyone"
DISCOVERY_ENDPOINT = "/ping"


def process_descriptor_str():
    return f"{socket.gethostname()}-{os.getpid()}-{INSTANCE_UUID}"


def main():
    print(process_descriptor_str())


if __name__ == "__main__":
    main()
    exit(0)


import logging
import discord
from discord.ext import commands, tasks


log = logging.getLogger("distributed")
log.setLevel(logging.DEBUG)


@dataclass()
class Packet:
    id: str = ""
    src: str = ""
    dst: str = ""
    endpoint: str = ""
    body: dict = field(default_factory=dict)
    backlink: str = ""



def make_packet(dst, endpoint, **body):
    p = Packet()
    p.body = body
    p.endpoint = endpoint
    p.src = CALLER_ID
    p.dst = dst
    p.id = str(uuid.uuid4())
    return p


def make_response_packet(inp: Packet, **body):
    p = Packet()
    p.body = body
    p.endpoint = inp.endpoint
    p.src = CALLER_ID
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


ENDPOINTS = {}


def endpoint(name):
    def ret(functor):
        ENDPOINTS[name] = functor
        return functor
    return ret


@endpoint("/ping")
async def ping(**args):
    return {"whoami": process_descriptor_str(),
        "endpoints": list(ENDPOINTS.keys())}


@endpoint("/add")
async def add(**args):
    return {"result": args["x"] + args["y"] + args["z"]}


class NetworkNode(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.comms_channel = None


    async def send_packet(self, packet):
        log.info(f"SEND: {packet}")
        await self.comms_channel.send(json.dumps(asdict(packet)))


    @commands.Cog.listener()
    async def on_ready(self):
        self.comms_channel = self.bot.get_channel(NODE_COMMS_CHANNEL_ID)
        p = make_packet(EVERYONE_WILDCARD, DISCOVERY_ENDPOINT)
        await self.send_packet(p)
        log.info("Logged into node communications channel #" \
            f"{self.comms_channel} as {CALLER_ID}")
        k = make_packet("#everyone", "/add", x=4, y=12, z=-3)
        await self.send_packet(k)


    @commands.Cog.listener()
    async def on_message(self, message):

        if message.channel != self.comms_channel:
           return

        p = cast_to_packet(message.content)

        if not p or p.src == CALLER_ID:
            return

        if p.dst != CALLER_ID and p.dst != EVERYONE_WILDCARD:
            return

        log.info(f"RECV: {p}")

        if p.endpoint in ENDPOINTS and not p.backlink:
            log.debug(f"Processing packet with endpoint {p.endpoint}")
            func = ENDPOINTS[p.endpoint]
            try:
                resp = await func(**p.body)
            except Exception as e:
                resp = {"error": f"{e}", "error_type": f"{type(e).__name__}"}
            q = make_response_packet(p, **resp)
            await self.send_packet(q)

