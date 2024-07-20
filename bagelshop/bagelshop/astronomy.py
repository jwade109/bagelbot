import requests
from dataclasses import dataclass, field
from datetime import datetime
from dacite import from_dict
from typing import Any, Optional, List
from bagelshop.logging import log
import discord


# https://api.nasa.gov/

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


def get_apod(api_key, when: datetime = None, random: bool = False):
    if when is None:
        when = datetime.now()
    params = {"api_key": api_key,
        "date": when.strftime(APOD_DATE_FMT),
        "thumbs": True}
    if random:
        params["count"] = 1
        del params["date"]
    r = try_request(APOD_ENDPOINT, params)
    print(r)
    d = r.json()
    if random:
        d = d[0]
    apod = from_dict(data_class=APOD, data=d)
    apod.stamp = datetime.strptime(apod.date, APOD_DATE_FMT)
    return apod


def get_rovers(api_key):
    params = {"api_key": api_key}
    r = try_request(MARS_ROVERS_ENDPOINT, params)
    d = r.json()
    ret = []
    for e in d["rovers"]:
        parsed = from_dict(data_class=Rover, data=e)
        ret.append(parsed)
    return ret


def get_random_picture(api_key, rover: Rover, sol: int = 0):
    params = {"api_key": api_key, "sol": sol}
    r = try_request(f"{MARS_ROVERS_ENDPOINT}/{rover.name}/photos", params)
    d = r.json()
    for e in d["photos"]:
        parsed = from_dict(data_class=RoverPhoto, data=e)
        return parsed
    return None


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
