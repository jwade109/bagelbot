
import os
import socket
import uuid
from dataclasses import dataclass, field, asdict
import json
import discord
from .logging import log


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


async def endpoint_ping(node_iface, **args):
    """
    args: none
    returns: node information
    """
    return {
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "instance": node_iface.instance_uuid,
        "endpoints": list(node_iface.endpoints.keys())
    }


async def endpoint_add(node_iface, **args):
    """
    args: x, y, z
    returns: x + y + z
    """
    return {"result": float(args["x"]) + float(args["y"]) + float(args["z"])}


async def endpoint_camera(node_iface, **args):
    """
    args: none
    returns: result=OK
    """
    return {"result": "OK"}


async def endpoint_ep_info(node_iface, **args):
    """
    args: endpoint
    returns: endpoint info
    """
    if not "name" in args:
        return {"endpoints": list(node_iface.endpoints.keys())}
    ep = args["name"]
    if ep not in node_iface.endpoints:
        return bad_endpoint_body(node_iface.caller_id, ep)
    func = node_iface.endpoints[ep]
    doc = func.__doc__
    doclines = [l.strip() for l in doc.split("\n") if l.strip()] if doc else []
    return {"endpoint": ep, "funcname": func.__name__, "doc": doclines}


def should_respond(caller_id, packet: Packet):
    if packet.backlink:
        return False
    if packet.dst == caller_id or packet.dst == EVERYONE_WILDCARD:
        return True
    if packet.src == caller_id:
        return False
    return packet.dst == caller_id or \
           packet.dst == ANYONE_WILDCARD


def packet_to_embed(p):

    c = discord.Color.green()
    if "error" in p.body:
        c = discord.Color.red()
    elif p.backlink:
        c = discord.Color.blue()
    embed = discord.Embed(title=f"[{p.endpoint}] {p.src} -> {p.dst}", color=c)
    for k, v in p.body.items():
        embed.add_field(name=str(k), value=str(v))
    footer = f"ID: {p.id}"
    if p.backlink:
        footer += f"\nB: {p.backlink}"
    embed.set_footer(text=footer)
    return embed


def register_endpoint(bot, name, func):
    node_iface = bot.get_cog(NODE_COG_NAME)
    if not node_iface:
        log.warn(f"Failed to register endpoint {name}")
    else:
        node_iface.register_endpoint(name, func)

