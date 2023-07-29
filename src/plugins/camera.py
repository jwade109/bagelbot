import discord
from discord.ext import commands, tasks
import bot_common
from resource_paths import stamped_fn
import suntime
from datetime import datetime, timedelta
import logging
from bblog import log
import plugins.distributed as distributed
import cv2
from typing import Any, List
from dataclasses import dataclass
import random
import requests


# TODO deduplicate this with voice.py
#
# downloads a file from the given URL to a filepath destination;
# doesn't check if the destination file already exists, or if
# the path is valid at all
def download_file(url, destination):
    log.info(f"Downloading file at {url} to {destination}.")
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) " \
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    response = requests.get(url, headers=headers)
    bin = response.content
    file = open(destination, "wb")
    if not file:
        log.error(f"Failed to open {destination}.")
    file.write(bin)
    file.close()


# get the datetime of today's sunrise; will return a time in the past if after sunrise
def get_sunrise_today(lat, lon):
    sun = suntime.Sun(lat, lon)
    now = datetime.now()
    real_sunrise = sun.get_local_sunrise_time(now).replace(tzinfo=None)
    return real_sunrise + timedelta(minutes=30)


@dataclass()
class BagelCam:
    name: str = ""
    type: str = ""
    desc: Any = ""
    picamera: Any = None # capture device if persistent
    sunrise: bool = False


async def take_still(node_iface, camera: BagelCam):
    fn = stamped_fn(f"cap-{camera.name}", "jpg")
    if camera.type == "picamera":
        camera.picamera.resolution = STILL_RESOLUTION
        camera.picamera.capture(fn)
    elif camera.type == "usb" or camera.type == "ip":
        cam = cv2.VideoCapture(camera.desc)
        _, frame = cam.read()
        cv2.imwrite(fn, frame)
    elif camera.type == "bagelnet":
        nodename, camera_name = camera.desc.split("/")
        log.info(f"Calling camera API for node {nodename}, camera {camera_name}")
        packets = await node_iface.call_endpoint(nodename, "/camera", 1, name=camera_name)
        if not packets:
            raise IOError(f"Failed to fetch network camera {camera_name} at node {nodename}")
        p = packets[0]
        url = p.body["url"]
        download_file(url, fn)
    else:
        raise IOError(f"Camera type \"{camera.type}\" not supported")
    return fn


def make_cameras(**kwargs) -> List[BagelCam]:
    cameras = kwargs.get("cameras", [])
    ret = {}
    for cam in cameras:
        b = BagelCam()
        b.name = cam["name"]
        b.type = cam["type"]
        b.desc = cam["desc"]
        if b.type == "picamera":
            try:
                from picamera import PiCamera
                b.picamera = PiCamera()
            except Exception as e:
                log.error(f"Failed to init picamera: {e}")
                continue
        ret[b.name] = b
        log.info(f"Add camera: {b.name}")
    return ret


def get_named_camera(cameras, name):
    if not cameras:
        return None
    if not name:
        return random.choice(list(cameras.values()))
    elif name not in cameras:
        return None
    return cameras[name]


STILL_RESOLUTION = (3280, 2464)
VIDEO_RESOLUTION = (1080, 720)


class Camera(commands.Cog):

    def __init__(self, bot, **kwargs):

        self.bot = bot

        self.cameras = make_cameras(**kwargs)
        if not self.cameras:
            log.error("NO CAMERAS SUPPORTED ON THIS DEVICE")

        # self.timelapse_active = False
        # self.last_still_capture = None
        # self.last_dt_to_sunrise = None

        # if sunrise_timer:
        #     srtime = get_sunrise_today(*self.location)
        #     self.location = bot_common.request_location()
        #     self.sunrise_capture.start()
        #     log.debug(f"Started sunrise timer.")

        async def testy_test(node_iface, **kwargs):
            """
            returns an image from the specified camera
            args: name - the name of the camera of interest
            """
            list_cams = kwargs.get("list", False)
            if list_cams:
                return {"cameras": [b.name for b in self.cameras.values()]}
            name = kwargs.get("name", "")
            cam = get_named_camera(self.cameras, name)
            if not cam:
                raise KeyError(f"Failed to get camera \"{name}\"")
            if cam.type == "bagelnet":
                raise IOError(f"Refusing to forward request for network camera \"{cam.name}\"")
            fn = await take_still(node_iface, cam)
            url = await node_iface.send_file(fn)
            return {"result": "OK", "camera": cam.name, "url": url}

        distributed.register_endpoint(bot, "/camera", testy_test)


    # @tasks.loop(minutes=2)
    # async def sunrise_capture(self):
    #     srtime = get_sunrise_today(*self.location)
    #     now = datetime.now()
    #     dt_to_sunrise = srtime - now
    #     if self.last_dt_to_sunrise and dt_to_sunrise < timedelta() and self.last_dt_to_sunrise >= timedelta():
    #         log.info(f"Sunrise reported as {srtime}, which is roughly now.")
    #         filename = stamped_fn("sunrise", "jpg")
    #         self.take_still(filename)
    #     self.last_dt_to_sunrise = dt_to_sunrise


    @commands.command(help="Look through Bagelbot's eyes.")
    async def capture(self, ctx, name: str = ""):
        names = ', '.join([b.name for b in self.cameras.values()])
        if not self.cameras:
            await ctx.send("No cameras are available.")
            return
        if len(self.cameras) == 1:
            cam = list(self.cameras.values())[0]
        elif not name:
            await ctx.send(f"Please provide the name of a camera: {names}")
            return
        else:
            cam = get_named_camera(self.cameras, name)
        if not cam:
            return await ctx.send(f"Camera \"{name}\" not available. Available cameras are: {names}")
        node_iface = self.bot.get_cog(distributed.NODE_COG_NAME)
        fn = await take_still(node_iface, cam)
        await ctx.send(file=discord.File(fn))


    # @commands.command(aliases=["day"], help="See the latest pictures of sunrise.")
    # async def sunrise(self, ctx, *options):
    #     log.debug(f"Mmmm, {ctx.message.author} wants it to be day. (opts={options})")
    #     files = glob(GENERATED_FILES_DIR + "/sunrise*.jpg")
    #     if not files:
    #         await ctx.send("Sorry, I don't have any pictures of sunrise to show you.")
    #         return
    #     choice = random.choice(files)
    #     if "today" in options or "latest" in options:
    #         files = sorted(files)
    #         choice = files[-1]
    #     log.info(f"File of choice: {choice}")
    #     result = re.search("sunrise-(.*).jpg", os.path.basename(choice))
    #     to_parse, _ = result.groups(1)[0].split(".")
    #     stamp = datetime.strptime(to_parse, "%Y-%m-%dT%H-%M-%S")
    #     await ctx.send(stamp.strftime('%I:%M %p on %B %d, %Y'), file=discord.File(choice))
