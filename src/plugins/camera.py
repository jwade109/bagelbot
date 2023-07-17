import discord
from discord.ext import commands, tasks
import bot_common
from resource_paths import stamped_fn
import suntime
from datetime import datetime, timedelta
import logging
from bblog import log
import plugins.distributed as distributed


# get the datetime of today's sunrise; will return a time in the past if after sunrise
def get_sunrise_today(lat, lon):
    sun = suntime.Sun(lat, lon)
    now = datetime.now()
    real_sunrise = sun.get_local_sunrise_time(now).replace(tzinfo=None)
    return real_sunrise + timedelta(minutes=30)


class Camera(commands.Cog):

    def __init__(self, bot):
        try:
            from picamera import PiCamera
            self.camera = PiCamera()
        except ImportError:
            self.camera = None
            log.error("NO CAMERA SUPPORTED ON THIS DEVICE")
        self.bot = bot
        self.STILL_RESOLUTION = (3280, 2464)
        self.VIDEO_RESOLUTION = (1080, 720)

        self.timelapse_active = False
        self.last_still_capture = None
        self.location = bot_common.request_location()
        self.sunrise_capture.start()
        self.last_dt_to_sunrise = None

        srtime = get_sunrise_today(*self.location)
        log.debug(f"For reference, sunrise time today is {srtime}.")

        async def testy_test(node_iface, **kwargs):
            if not self.camera:
                raise IOError("No camera on this device")
            fn = stamped_fn("cap", "jpg")
            self.take_still(fn)
            url = await node_iface.send_file(fn)
            return {"result": "OK", "url": url}

        distributed.register_endpoint(bot, "/camera", testy_test)


    @tasks.loop(minutes=2)
    async def sunrise_capture(self):
        srtime = get_sunrise_today(*self.location)
        now = datetime.now()
        dt_to_sunrise = srtime - now
        if self.last_dt_to_sunrise and dt_to_sunrise < timedelta() and self.last_dt_to_sunrise >= timedelta():
            log.info(f"Sunrise reported as {srtime}, which is roughly now.")
            filename = stamped_fn("sunrise", "jpg")
            self.take_still(filename)
        self.last_dt_to_sunrise = dt_to_sunrise

    def take_still(self, filename):
        log.debug(f"Writing camera capture to {filename}.")
        self.camera.resolution = self.STILL_RESOLUTION
        self.camera.capture(filename)

    async def take_video(self, filename, seconds):
        log.debug(f"Writing camera capture ({seconds} seconds) to {filename}.")
        self.camera.resolution = self.VIDEO_RESOLUTION
        self.camera.start_recording(filename)
        await asyncio.sleep(seconds+1)
        self.camera.stop_recording()
        log.debug(f"Done: {filename}.")

    @commands.command(help="Look through Bagelbot's eyes.")
    async def capture(self, ctx, seconds: float = None):
        if not seconds:
            filename = stamped_fn("cap", "jpg")
            self.take_still(filename)
            await ctx.send(file=discord.File(filename))
            return
        if seconds > 60 and not is_wade(ctx):
            await ctx.send("I don't support capture durations greater than 60 seconds.")
            return
        await ctx.send(f"Recording for {seconds} seconds.")
        filename = stamped_fn("cap", "h264")
        await self.take_video(filename, seconds)
        await ctx.send("Done.")
        file_size = os.path.getsize(filename)
        limit = 8 * 1024 * 1024
        if file_size < limit:
            await ctx.send(file=discord.File(filename))
        else:
            await ctx.send("Video is too large for message embed. It can be " \
                "transferred from the Raspberry Pi (by someone on the LAN) " \
                f"using this command: `scp pi@10.0.0.137:{filename} .`")

    # @commands.command(name="timelapse-start", help="Start timelapse.")n
    async def timelapse_start(self, ctx):
        log.debug("Enabling timelapse capture.")
        self.timelapse_active = True
        await ctx.send("timelapse_active = True")

    # @commands.command(name="timelapse-stop", help="Stop timelapse.")
    async def timelapse_stop(self, ctx):
        log.debug("Disabling timelapse capture.")
        self.timelapse_active = False
        await ctx.send("timelapse_active = False")

    @commands.command(aliases=["day"], help="See the latest pictures of sunrise.")
    async def sunrise(self, ctx, *options):
        log.debug(f"Mmmm, {ctx.message.author} wants it to be day. (opts={options})")
        files = glob(GENERATED_FILES_DIR + "/sunrise*.jpg")
        if not files:
            await ctx.send("Sorry, I don't have any pictures of sunrise to show you.")
            return
        choice = random.choice(files)
        if "today" in options or "latest" in options:
            files = sorted(files)
            choice = files[-1]
        log.info(f"File of choice: {choice}")
        result = re.search("sunrise-(.*).jpg", os.path.basename(choice))
        to_parse, _ = result.groups(1)[0].split(".")
        stamp = datetime.strptime(to_parse, "%Y-%m-%dT%H-%M-%S")
        await ctx.send(stamp.strftime('%I:%M %p on %B %d, %Y'), file=discord.File(choice))
