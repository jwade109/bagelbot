import requests
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from dacite import from_dict
from typing import Any, Optional, List
import logging
import sys
import random
from state_machine import get_param


log = logging.getLogger("astronomy")
log.setLevel(logging.DEBUG)


# https://api.nasa.gov/

NASA_API_KEY = get_param("NASA_API_KEY", "")
APOD_DATE_FMT = "%Y-%m-%d"
APOD_ENDPOINT = "https://api.nasa.gov/planetary/apod"
MARS_ROVERS_ENDPOINT = "https://api.nasa.gov/mars-photos/api/v1/rovers"


@dataclass()
class APOD:
    date: str = ""
    stamp: datetime = None
    title: str = ""
    explanation: str = ""
    url: str = ""
    hdurl: str = ""
    copyright: str = ""
    media_type: str = ""
    thumbnail_url: str = ""
    service_version: str = ""
    resource: str = ""


@dataclass()
class Camera:
    id: int = 0
    name: str = ""
    rover_id: int = 0
    full_name: str = ""


@dataclass()
class Rover:
    id: int = 0
    name: str = ""
    landing_date: str = ""
    launch_date: str = ""
    status: str = ""
    max_sol: int = 0
    max_date: str = ""
    total_photos: int = 0
    cameras: List[Camera] = field(default_factory=list)


@dataclass()
class RoverPhoto:
    id: int = 0
    sol: int = 0
    camera: Camera = field(default_factory=Camera)
    img_src: str = ""


def try_request(url, params):
    log.debug(f"{url}, {params}")
    r = requests.get(url, params=params)
    if r.status_code != 200:
        log.error(f"Request failed (code {r.status_code}): {r.text}")
        return None
    return r


def get_webpage_url(apod: APOD) -> str:
    yy = apod.stamp.year % 2000
    mm = apod.stamp.month
    dd = apod.stamp.day
    return f"https://apod.nasa.gov/apod/ap{yy:02d}{mm:02d}{dd:02d}.html"


def get_apod(when: datetime = None, random: bool = False):
    if when is None:
        when = datetime.now()
    params = {"api_key": NASA_API_KEY,
        "date": when.strftime(APOD_DATE_FMT),
        "thumbs": True}
    if random:
        params["count"] = 1
        del params["date"]
    r = try_request(APOD_ENDPOINT, params)
    d = r.json()
    if random:
        d = d[0]
    apod = from_dict(data_class=APOD, data=d)
    apod.stamp = datetime.strptime(apod.date, APOD_DATE_FMT)
    return apod


def get_rovers():
    params = {"api_key": NASA_API_KEY}
    r = try_request(MARS_ROVERS_ENDPOINT, params)
    d = r.json()
    ret = []
    for e in d["rovers"]:
        parsed = from_dict(data_class=Rover, data=e)
        ret.append(parsed)
    return ret


def get_random_picture(rover: Rover, sol: int = 0):
    params = {"api_key": NASA_API_KEY, "sol": sol}
    r = try_request(f"{MARS_ROVERS_ENDPOINT}/{rover.name}/photos", params)
    d = r.json()
    for e in d["photos"]:
        parsed = from_dict(data_class=RoverPhoto, data=e)
        return parsed
    return None


def main():
    rover = [r for r in get_rovers() if r.name == "Perseverance"][0]
    sol = random.randint(1, rover.max_sol)
    pic = get_random_picture(rover, sol)
    if not pic:
        print(f"No pics on sol {sol}.")
        return 1
    print(rover.name, pic.camera.name, pic.img_src)
    return 0


if __name__ == "__main__":

    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
        format="[%(levelname)s] %(message)s")
    main()


import discord
from discord.ext import commands, tasks


def cutoff_at_n(s: str, n: int, suffix: str = "") -> str:
    if len(s) < n:
        return s
    return s[:n] + suffix


def apod_to_embed(apod: APOD) -> discord.Embed:

    embed = discord.Embed(title=apod.title, url=get_webpage_url(apod))
    embed.add_field(name=apod.stamp.strftime("%A, %B %d, %Y"),
        value=cutoff_at_n(apod.explanation, 300, "..."), inline=False)
    embed.set_footer(text="NASA Astronomy Picture of the Day")
    embed.set_image(url=apod.hdurl)
    if apod.media_type == "video":
        embed.set_image(url=apod.thumbnail_url)
        embed.add_field(name="Video Link", value=apod.url, inline=False)
    return embed


def nasalike_to_embed(nasalike: Any) -> Optional[discord.Embed]:
    if isinstance(nasalike, APOD):
        return apod_to_embed(nasalike)
    return None


def str_to_datetime(s: str) -> Optional[datetime]:
    try:
        return datetime.strptime(s, APOD_DATE_FMT)
    except:
        return None


class Astronomy(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def apod(self, ctx, when: str = ""):
        if when == "*":
            apod = get_apod(None, True)
        else:
            dt = str_to_datetime(when)
            if when and not dt:
                await ctx.send("Bad 'when' argument: Requires dates of the form YYYY-MM-DD.")
                return
            apod = get_apod(dt)
        await ctx.send(embed=apod_to_embed(apod))
