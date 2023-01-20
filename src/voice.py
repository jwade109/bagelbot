import discord
from discord.ext import commands, tasks
from discord.utils import get
from discord import FFmpegPCMAudio
from dataclasses import dataclass, field
from datetime import datetime
import collections
from state_machine import get_param, set_param
from resource_paths import *
from predicates import *
import random
from glob import glob
from fuzzywuzzy import process
from gtts import gTTS
from youtube_dl import YoutubeDL
from pathlib import Path
import asyncio
from ws_dir import WORKSPACE_DIRECTORY
import requests
import logging
import moonbase


log = logging.getLogger("voice")
log.setLevel(logging.DEBUG)


# loudness ratio, out of 100
SOUND_EFFECT_VOLUME = 34
MUSIC_VOLUME = 10
MOONBASE_VOLUME = 100


class TrackedFFmpegPCMAudio(FFmpegPCMAudio):
    def __init__(self, name, *args, **kwargs):
        print(f"Init: {name}.")
        self.on_read = None
        self.name = name
        self.read_ops = 0
        super().__init__(*args, **kwargs)
    def read(self):
        if self.on_read:
            self.on_read(self.name, self.read_ops)
        self.read_ops += 1
        return super().read()


# struct for audio source; support for audio stored on the filesystem (path)
# or network-streamed audio (url). only one should be populated
@dataclass()
class AudioSource:
    path: str = None
    url: str = None


# struct for audio queue element; audio plus context information for
# informing the user about the status of the request
@dataclass()
class QueuedAudio:
    name: str
    pretty_url: str
    source: AudioSource
    context: discord.ext.commands.Context
    reply_to: bool = False
    disconnect_after: bool = False
    looped: bool = True
    volume: int = 50


# audio queue struct; on a per-server basis, represents an execution
# state for playing audio and enqueueing audio requests
@dataclass()
class AudioQueue:
    last_played: datetime
    playing_flag = False
    now_playing: QueuedAudio = None
    music_queue: collections.deque = field(default_factory=collections.deque)
    effects_queue: collections.deque = field(default_factory=collections.deque)


# initiates connection to a voice channel
async def join_voice(bot, ctx, channel):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if not voice or voice.channel != channel:
        if voice:
            await voice.disconnect()
        await channel.connect()


# will attempt to join a voice channel according to these strategies:
# - will try to join the VC of the requester, if relevant/possible
# - if not, will join a random populated voice channel
# - if no channels are populated, will join a random VC
async def ensure_voice(bot, ctx, allow_random=False):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if ctx.author.voice:
        await join_voice(bot, ctx, ctx.author.voice.channel)
        return
    options = [x for x in ctx.guild.voice_channels if len(x.voice_states) > 0]
    if not options:
        if allow_random:
            options = ctx.guild.voice_channels
        if not options:
            return
    choice = random.choice(options)
    await join_voice(bot, ctx, choice)


# returns a unique filename stamped with the current time.
# good for files we want to look at later
def stamped_fn(prefix, ext, dir=GENERATED_FILES_DIR):
    if not os.path.exists(dir):
        os.mkdir(dir)
    return f"{dir}/{prefix}-{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.{ext}"


# returns a unique filename in /tmp; for temporary work
# which is not intended to persist past reboots
def tmp_fn(prefix, ext):
    return stamped_fn(prefix, ext, "/tmp/bagelbot")


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


# converts text to a google text to speech file, and returns
# the filename of the resultant file
def soundify_text(text, lang, tld):
    tts = gTTS(text=text, lang=lang, tld=tld)
    filename = tmp_fn("say", "mp3")
    tts.save(filename)
    return filename


# constructs an audio stream object from an audio file,
# for streaming via discord audio API
def file_to_audio_stream(filename):
    if os.name == "nt": # SOL
        return TrackedFFmpegPCMAudio(filename, executable="ffmpeg.exe",
            source=filename, options="-loglevel panic")
    return TrackedFFmpegPCMAudio(filename, executable="/usr/bin/ffmpeg",
        source=filename, options="-loglevel panic")


# constructs an audio stream object from the URL
# pointing to such a stream
def stream_url_to_audio_stream(url):
    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }
    return TrackedFFmpegPCMAudio(url, url, **FFMPEG_OPTIONS)


# converts a youtube video URL to an audio stream object,
# or several stream objects in the case of youtube playlist URLs
def youtube_to_audio_stream(url):
    log.debug(f"Converting YouTube audio: {url}")

    # don't ask me what these mean, no one knows
    YDL_OPTIONS = {
        'format': 'bestvideo+bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192'
        }],
        'postprocessor_args': [
            '-ar', '16000'
        ],
        'prefer_ffmpeg': True,
        'keepvideo': False
    }

    # youtube format codes:
    # https://gist.github.com/sidneys/7095afe4da4ae58694d128b1034e01e2#youtube-video-stream-format-codes
    # https://gist.github.com/AgentOak/34d47c65b1d28829bb17c24c04a0096f
    FORMATS_IN_DECREASING_ORDER_OF_PREFERENCE = [
        # DASH audio formats
        249, # WebM     Opus    (VBR) ~50 Kbps
        250, # WebM     Opus    (VBR) ~70 Kbps
        251, # WebM     Opus    (VBR) <=160 Kbps

        140, # m4a    audio          128k
        18,  # mp4    audio/video    360p
        22,  # mp4    audio/video    720p

        # Livestream formats
        93, # MPEG-TS (HLS)    360p    AAC (LC)     128 Kbps    Yes
        91, # MPEG-TS (HLS)    144p    AAC (HE v1)  48 Kbps     Yes
        92, # MPEG-TS (HLS)    240p    AAC (HE v1)  48 Kbps     Yes
        94, # MPEG-TS (HLS)    480p    AAC (LC)     128 Kbps    Yes
        95, # MPEG-TS (HLS)    720p    AAC (LC)     256 Kbps    Yes
        96, # MPEG-TS (HLS)    1080p   AAC (LC)     256 Kbps    Yes
    ]

    try:
        extracted_info = YoutubeDL(YDL_OPTIONS).extract_info(url, download=False)
    except Exception as e:
        log.error(f"Failed to extract YouTube info: {e}")
        return None
    if not extracted_info:
        log.info("Failed to get YouTube video info.")
        return []
    to_process = []
    if "format" not in extracted_info and "entries" in extracted_info:
        log.debug("Looks like this is a playlist.")
        to_process = extracted_info["entries"]
    else:
        to_process.append(extracted_info)
    log.debug(f"Processing {len(to_process)} videos.")
    ret = []
    for info in to_process:
        if "thumbnails" in info:
            thumbnails = sorted(info["thumbnails"], key=lambda t: t["width"])
            if thumbnails:
                fn = tmp_fn("thumbnail", "jpg")
                download_file(thumbnails[-1]["url"], fn)
        formats = info["formats"]
        if not formats:
            log.debug("Failed to get YouTube video info.")
            continue
        selected_fmt = None
        log.debug(f"{len(formats)} formats: " + ", ".join(sorted([f["format_id"] for f in formats])))
        log.debug(f"Preferred formats: {FORMATS_IN_DECREASING_ORDER_OF_PREFERENCE}")
        for format_id in FORMATS_IN_DECREASING_ORDER_OF_PREFERENCE:
            for fmt in formats:
                try:
                    if int(fmt["format_id"]) == format_id:
                        selected_fmt = fmt
                        print(f"Found preferred format {format_id}.")
                        break
                except Exception as e:
                    log.error(f"UH OH BAD TIMES: {fmt}\n{e}")
                    continue
            if selected_fmt is not None:
                break
        if selected_fmt is None:
            log.debug("Couldn't find preferred format; falling back on default.")
            selected_fmt = formats[0]
        log.debug(f"Playing stream ID {selected_fmt['format_id']}.")
        stream_url = selected_fmt["url"]
        ret.append((info, stream_url))
    log.debug(f"Produced {len(ret)} audio streams.")
    return ret


# given a directory and search key, will select a random sound file
# in the directory or any subdirectories whose filename is a fuzzy
# match for the search key. good for providing users with unstructured
# and fault-tolerant search functions for sound effect commands
def choose_from_dir(directory, search_key):
    log.debug(f"directory: {directory}, search: {search_key}")
    files = glob(f"{directory}/*.mp3") + glob(f"{directory}/**/*.mp3") + \
            glob(f"{directory}/*.ogg") + glob(f"{directory}/**/*.ogg") + \
            glob(f"{directory}/*.wav") + glob(f"{directory}/**/*.wav")
    if not files:
        log.error(f"No files to choose from in {directory}.")
        return ""
    choice = random.choice(files)
    if search_key:
        search_key = " ".join(search_key)
        choices = process.extract(search_key, files)
        choices = [x[0] for x in choices if x[1] == choices[0][1]]
        choice = random.choice(choices)
    log.debug(f"choice: {choice}")
    return choice


# asks a humorous web API for an ad string
def get_advertisement():
    try:
        r = requests.get(f"https://api.isevenapi.xyz/api/iseven/2/")
        d = r.json()
        return d["ad"]
    except Exception:
        return None


def on_audio_end(*args):
    log.info(f"Audio has completed with these args: {args}")


class Voice(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.now_playing = {}
        self.global_accent = get_param("global_accent", "american")
        self.accents = {
            "australian":       ("en", "com.au"),
            "british":          ("en", "co.uk"),
            "american":         ("en", "com"),
            "canadian":         ("en", "ca"),
            "indian":           ("en", "co.in"),
            "irish":            ("en", "ie"),
            "south african":    ("en", "co.za"),
            "french canadian":  ("fr", "ca"),
            "french":           ("fr", "fr"),
            "mandarin":         ("zh-CN", "com"),
            "taiwanese":        ("zh-TW", "com"),
            "brazilian":        ("pt", "com.br"),
            "portuguese":       ("pt", "pt"),
            "mexican":          ("es", "com.mx"),
            "spanish":          ("es", "es"),
            "spanish american": ("es", "com"),
            "dutch":            ("nl", "com"),
            "german":           ("de", "com")
        }
        log.debug(f"Default accent is {self.global_accent}, " \
                  f"{self.accents[self.global_accent]}")
        self.audio_driver_checked.start()
        self.current_narration_channels = {}

    async def enqueue_audio(self, queued_audio):
        guild = queued_audio.context.guild
        if guild not in self.queues:
            log.debug(f"New guild audio queue: {guild}")
            self.queues[guild] = AudioQueue(datetime.now())
        log.debug(f"Enqueueing audio: guild={guild}, audio={queued_audio.name}")
        self.queues[guild].music_queue.append(queued_audio)

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author == self.bot.user:
            return

        if message.channel.id not in self.current_narration_channels:
            return

        self.current_narration_channels[message.channel.id] += 1
        if self.current_narration_channels[message.channel.id] == 1:
            return

        log.debug(message.channel)
        log.debug(self.current_narration_channels)
        log.debug(f"Narrating: {message}")

        ctx = await self.bot.get_context(message)

        await self.moonbase(ctx, message.content)


    @commands.command(aliases=["en"])
    async def enable_narration(self, ctx):
        self.current_narration_channels[ctx.channel.id] = 0
        await ctx.send(f"Enabled narration for {ctx.channel.mention}.")

    @commands.command(aliases=["dn"])
    async def disable_narration(self, ctx):
        if ctx.channel.id in self.current_narration_channels:
            del self.current_narration_channels[ctx.channel.id]
        await ctx.send(f"Disabled narration for {ctx.channel.mention}.")

    # @commands.Cog.listener()
    # async def on_voice_state_update(self, member, before, after):

    #     def to_str(state):
    #         loc = f"{state.channel.guild if state.channel else '--'} / {state.channel}"
    #         if state.channel:
    #             vcs = [i for i in state.channel.voice_states if i != self.bot.user.id]
    #             loc += f" ({len(vcs)} non-self clients connected)"
    #         return loc

    #     log.debug(f"Voice state change...\n\n  {member}:\n  " \
    #         f"Before: {to_str(before)}\n  After:  {to_str(after)}\n")

    @tasks.loop(seconds=0.5)
    async def audio_driver_checked(self):
        try:
            for guild, audio_queue in self.queues.items():
                await self.handle_audio_queue(guild, audio_queue)
        except Exception as e:
            uhoh = f"Uncaught exception in audio driver: {type(e)} {e}"
            print(uhoh)
            print(e.__traceback__)
            log.error(uhoh)
            log.error(e.__traceback__)

    async def handle_audio_queue(self, guild, audio_queue):
        voice = get(self.bot.voice_clients, guild=guild)
        if voice:
            num_peers = len(voice.channel.voice_states) - 1
            if voice and not num_peers:
                log.info("Seems like nobody is here; disconnecting.")
                await voice.disconnect()
                return
        np = self.get_now_playing(guild)
        if np:
            audio_queue.now_playing = np
            audio_queue.last_played = datetime.now()
            print(f"{audio_queue.last_played}: {guild} " \
                f"is playing {np.name} for {num_peers} users.")
        else:
            disconnect_after = False
            if audio_queue.now_playing:
                disconnect_after = audio_queue.now_playing.disconnect_after
            audio_queue.now_playing = None
            audio_queue.playing_flag = False
            if disconnect_after and voice:
                await voice.disconnect()
        if not audio_queue.music_queue:
            return
        if voice and (voice.is_playing() or voice.is_paused()):
            return
        log.debug("New jobs for the audio queue.")
        to_play = audio_queue.music_queue.popleft()
        log.info(f"Handling queue element: guild={to_play.context.guild}, audio={to_play.name}")
        await ensure_voice(self.bot, to_play.context)
        voice = get(self.bot.voice_clients, guild=to_play.context.guild)
        if not voice:
            log.error(f"Failed to connect to voice when trying to play {to_play}")
            return
        if to_play.reply_to:
            embed = discord.Embed(title=to_play.name, color=0xff3333)
            embed.set_author(name=to_play.context.author.name, icon_url=to_play.context.author.avatar_url)
            file = discord.File(PICTURE_OF_BAGELS, filename="bagels.jpg")
            embed.set_thumbnail(url="attachment://bagels.jpg")
            if to_play.pretty_url:
                embed.add_field(name="Now Playing", value=to_play.pretty_url)
            maybe_ad = get_advertisement()
            if maybe_ad:
                embed.set_footer(text=maybe_ad)
                log.debug(f"Delivering ad: {maybe_ad}")
            await to_play.context.reply(embed=embed, file=file, mention_author=False)
        if to_play.source.path is not None:
            audio = file_to_audio_stream(to_play.source.path)
            if not audio:
                log.error(f"Failed to convert from file (probably on Windows): {to_play.name}")
                return
        elif to_play.source.url is not None:
            audio = stream_url_to_audio_stream(to_play.source.url)
        else:
            log.error(f"Bad audio source: {to_play.name}")
            return
        print(f"{guild} is playing {to_play.name}")

        def on_read_throttled(name, ops):
            pass
            # if ops % 10 > 0:
            #     return
            # print(f"{name}: {ops/50:0.2f} seconds")

        audio.on_read = on_read_throttled
        audio_queue.playing_flag = True
        audio_queue.last_played = datetime.now()
        audio = discord.PCMVolumeTransformer(audio, volume=to_play.volume/100)
        voice.play(audio, after=on_audio_end)
        self.now_playing[guild] = to_play


    def get_now_playing(self, guild):
        voice = get(self.bot.voice_clients, guild=guild)
        if not voice or guild not in self.now_playing:
            return None
        # we're in voice, and there was a song playing at some point in the past.
        # see if it's still playing
        if voice.is_playing() or voice.is_paused():
            return self.now_playing[guild]
        del self.now_playing[guild]
        return None

    async def get_queue(self, ctx):
        if ctx.guild not in self.queues:
            self.queues[ctx.guild] = AudioQueue(datetime.now())
        return self.queues[ctx.guild]

    @commands.command(name="now-playing", aliases=["np", "shazam"], help="What song/ridiculous Star Wars quote is this?")
    async def now_playing(self, ctx):
        np = self.get_now_playing(ctx.guild)
        if np:
            await ctx.send(f"Playing: {np.name}")
        else:
            await ctx.send("Not currently playing anything.")

    @commands.command(aliases=["q"], help="What songs are up next?")
    async def queue(self, ctx):
        np = self.get_now_playing(ctx.guild)
        queue = await self.get_queue(ctx)
        if not queue and not np:
            await ctx.send("Nothing currently queued. Queue up music using the `play` command.")
            return
        lines = []
        if np:
            lines.append(f"Playing     {np.name}")
        for i, audio in enumerate(queue.music_queue):
            line = f"{i+1:<12}{audio.name}"
            lines.append(line)
        await ctx.send("```\n===== SONG QUEUE =====\n\n" + "\n".join(lines) + "\n```")

    async def clear_queue(self, guild):
        log.debug(f"Clearing song queue for guild {guild}.")
        if guild not in self.queues or not self.queues[guild]:
            return False
        del self.queues[guild]
        return True

    @commands.command(name="clear-queue", aliases=["clear", "cq"], help="Clear the song queue.")
    async def clear_queue_cmd(self, ctx):
        if await self.clear_queue(ctx.guild):
            await ctx.message.add_reaction("💥")
        else:
            await ctx.send("Nothing currently queued!", delete_after=5)

    # returns:
    # 0 if not in voice
    # 1 if in voice, but no song playing
    # 2 if in voice, and stopped the current song
    async def stop_playing_current_song_if_exists(self, guild):
        voice = get(self.bot.voice_clients, guild=guild)
        log.debug(f"Stopping current audio on {guild}.")
        if not voice:
            log.debug("No voice.")
            return 0
        if voice.is_playing() or voice.is_paused():
            log.debug("Stopping current audio.")
            voice.stop()
            return 2
        log.debug("No audio playing on voice instance.")
        return 1

    @commands.command(help="Skip whatever is currently playing.")
    async def skip(self, ctx):
        ret = await self.stop_playing_current_song_if_exists(ctx.guild)
        if ret == 0:
            await ctx.send("Not currently in voice!", delete_after=5)
        elif ret == 1:
            await ctx.send("Not currently playing anything!", delete_after=5)
        else:
            await ctx.send("Skipped.", delete_after=5)

    @commands.command(help="Pause or unpause whatever is currently playing.")
    async def pause(self, ctx):
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if not voice:
            await ctx.send("Not currently in voice!", delete_after=5)
        elif voice.is_playing():
            await ctx.message.add_reaction("⏸️")
            voice.pause()
        elif voice.is_paused():
            await ctx.message.add_reaction("▶️")
            voice.resume()

    @commands.command(help="Get or set the bot's accent.")
    async def accent(self, ctx, *argv):
        if not argv:
            await ctx.send(f"My current accent is \"{self.global_accent}\".")
            return
        arg = " ".join(argv).lower()
        available = ", ".join([x for x in self.accents])
        if arg == "help":
            await ctx.send("Set my accent using \"bb accent <accent>\". " \
                f"Available accents are: {available}")
            return
        if arg not in available:
            await ctx.send("Sorry, that's not a valid accent. " \
                f"Available accents are: {available}")
            return
        self.global_accent = arg
        set_param("global_accent", arg)
        await ctx.send(f"Set accent to \"{arg}\".")

    @commands.command(help="Leave voice chat.")
    async def leave(self, ctx):
        if not ctx.voice_client:
            await ctx.send("Not connected to voice!")
            return
        await ctx.voice_client.disconnect()

    @commands.command(help="Join voice chat.")
    async def join(self, ctx):
        if random.random() < 0.023:
            await self.enqueue_filesystem_sound(ctx, SWOOSH_PATH)
        else:
            await self.enqueue_filesystem_sound(ctx, HELLO_THERE_PATH)

    # @commands.command(help="Make Bagelbot speak to you.")
    # async def say(self, ctx, *message):
    #     await ensure_voice(self.bot, ctx)
    #     if not message:
    #         message = ["The lawnmower goes shersheeeeeeerrerererereeeerrr ",
    #                    "vavavoom sherererererere ruuuuuuuusususususkuskuskuksuksuus"]
    #     voice = get(self.bot.voice_clients, guild=ctx.guild)
    #     if not voice:
    #         if not ctx.author.voice:
    #             await ctx.send("You're not in a voice channel!")
    #             return
    #         channel = ctx.author.voice.channel
    #         await channel.connect()
    #     voice = get(self.bot.voice_clients, guild=ctx.guild)
    #     say = " ".join(message)
    #     filename = soundify_text(say, *self.accents[self.global_accent])
    #     source = AudioSource()
    #     source.path = filename
    #     await self.enqueue_audio(QueuedAudio(f"Say: {say}", None, source, ctx))

    @commands.command(help="Bagelbot has a declaration to make.")
    async def declare(self, ctx, *message):
        await ensure_voice(self.bot, ctx)
        if not message:
            message = ["Save the world. My final message. Goodbye."]
        if len(message) == 1 and message[0] == "bankruptcy":
            message = ["I. Declare. Bankruptcy!"]
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if not voice:
            if not ctx.author.voice:
                await ctx.send("You're not in a voice channel!")
                return
            channel = ctx.author.voice.channel
            await channel.connect()
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        filename = soundify_text(" ".join(message), *self.accents[self.global_accent])
        source = AudioSource()
        source.path = filename
        title = os.path.basename(filename)
        qa = QueuedAudio(title, None, source, ctx, False, True)
        await self.enqueue_audio(qa)

    async def await_queue_completion(self, guild):
        log.debug(f"Awaiting the completion of {guild}'s song queue.")
        if guild not in self.queues or not self.queues[guild]:
            log.debug(f"Guild {guild} has no queue.")
            return
        while True:
            np = self.get_now_playing(guild)
            queue_len = len(self.queues[guild].music_queue)
            log.info(f"Now playing: {np.name if np else '--'}, with {queue_len} remaining")
            if not np and not queue_len:
                break
            await asyncio.sleep(0.5)

    @commands.command(help="Tucks you and your friends into bed.")
    async def bedtime(self, ctx):
        bot_member = await ctx.guild.fetch_member(self.bot.user.id)
        log.debug(f"Permissions: {bot_member.guild_permissions}")
        perms = bot_member.guild_permissions
        if not perms.move_members:
            log.warn("Insufficient permissions.")
            await ctx.send("It looks like I don't have permission to " \
                "remove users from voice channels, which is required "
                "for this command to work. Please grant me the " \
                "\"Move Members\" permission and try again.")
            return
        log.debug(f"{ctx.message.author} wants everyone to go to bed.")
        await ensure_voice(self.bot, ctx)
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        member_uids = []
        if not voice:
            await ctx.send("Nobody is in voice... good night.")
            return
        if voice:
            member_uids = [i for i in voice.channel.voice_states if i != self.bot.user.id]
        log.debug(f"Voice members: {member_uids}")
        if not member_uids:
            await ctx.send("Nobody in voice!")
            return
        await ctx.send("It's time for bed!")
        await self.clear_queue(ctx.guild)
        await self.stop_playing_current_song_if_exists(ctx.guild)
        await self.say(ctx, "It's time to be a responsible adult and go to bed. Good night!")
        # not sure if this is necessary; maybe can kick via UID?
        members = [await ctx.guild.fetch_member(uid) for uid in member_uids]
        await self.await_queue_completion(ctx.guild)
        log.debug(f"Sending these troublemakers to bed: {' '.join(str(m) for m in members)}")
        for member in members:
            await member.move_to(None)

    async def enqueue_filesystem_sound(self, ctx, filename, is_effect=True, **kwargs):
        await ensure_voice(self.bot, ctx)
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if not voice:
            if not ctx.author.voice:
                await ctx.send("You're not in a voice channel!")
                return
            channel = ctx.author.voice.channel
            await channel.connect()
        await ctx.message.add_reaction("👍")
        source = AudioSource()
        source.path = filename
        title = os.path.basename(filename)
        if is_effect:
            title += " (effect)"
        qa = QueuedAudio(title, None, source, ctx, not is_effect)
        qa.volume = SOUND_EFFECT_VOLUME
        if "volume" in kwargs:
            qa.volume = kwargs["volume"]
        await self.enqueue_audio(qa)
        await asyncio.sleep(5)
        await ctx.message.remove_reaction("👍", self.bot.user)

    async def walk(self, ctx, directory):
        log.debug(f"Providing directory listing of {directory}.")
        def split_paragraph_at_newlines(paragraph, char_limit=1900):
            ret = []
            current = []
            for line in paragraph.split("\n"):
                current_paragraph = "\n".join(current)
                if len(current_paragraph) + len(line) <= char_limit:
                    current.append(line)
                else:
                    ret.append("\n".join(current))
                    current = []
            if current:
                ret.append("\n".join(current))
            return ret

        paths = Path(directory).rglob("*.*")
        if not paths:
            await ctx.send(f"Found no files in {directory}.")
            return
        reldir = os.path.relpath(directory, WORKSPACE_DIRECTORY)
        await ctx.send(f"Found these sound files in **{reldir}**.")

        def path_to_str(path):
            ret = os.path.relpath(str(path), directory)
            if len(ret) > 60:
                ret = ret[:57] + "..."
            return ret

        result = "\n".join(path_to_str(x) for x in paths)
        paginated = split_paragraph_at_newlines(result)
        for i, page in enumerate(paginated):
            title = f"Directory Listing of {reldir}"
            if len(paginated) > 1:
                title += f" ({i+1} of {len(paginated)})"
            await ctx.send(embed=discord.Embed(title=title,
                description=f"```\n{page}\n```"))

    @commands.command(name="genghis-khan", aliases=["gk", "genghis", "khan"],
        help="Something something a little bit Genghis Khan.")
    async def kahn(self, ctx):
        await self.enqueue_filesystem_sound(ctx, GK_PATH)

    async def generic_choosable_sound_effect(self, ctx, directory, search, is_effect=True):
        if "".join(search) == "?":
            return await self.walk(ctx, directory)
        choice = choose_from_dir(directory, search)
        if not choice:
            await ctx.send("Sorry, no sound effect files available.")
            return
        await self.enqueue_filesystem_sound(ctx, choice, is_effect)

    @commands.command(name="rocket-league", aliases=["rl"], help="THIS IS ROCKET LEAGUE!")
    async def rocket_league(self, ctx, *search):
        await self.generic_choosable_sound_effect(ctx, RL_DIRECTORY, search)

    @commands.command(aliases=["ut"], help="The music... it fills you with determination.")
    async def undertale(self, ctx, *search):
        await self.generic_choosable_sound_effect(ctx, UNDERTALE_DIRECTORY, search)

    @commands.command(aliases=["sw"], help="This is where the fun begins.")
    async def starwars(self, ctx, *search):
        await self.generic_choosable_sound_effect(ctx, STAR_WARS_DIRECTORY, search)

    @commands.command(aliases=["sb"], help="I'm ready!")
    async def spongebob(self, ctx, *search):
        await self.generic_choosable_sound_effect(ctx, SPONGEBOB_DIRECTORY, search)

    @commands.command(aliases=["sim"], help="Doh!")
    async def simpsons(self, ctx, *search):
        await self.generic_choosable_sound_effect(ctx, SIMPSONS_DIRECTORY, search)

    @commands.command(help="Nice on!")
    async def wii(self, ctx, *search):
        await self.generic_choosable_sound_effect(ctx, WII_EFFECTS_DIR, search)

    @commands.command(help="From the moment I understood the weakness of my flesh, it disgusted me.")
    async def mechanicus(self, ctx, *search):
        await self.generic_choosable_sound_effect(ctx, MECHANICUS_DIR, search, False)

    @commands.command(aliases=["jm"], help="I don't look older, I just look worse.")
    async def mulaney(self, ctx, *search):
        await self.generic_choosable_sound_effect(ctx, MULANEY_DIRECTORY, search)

    @commands.command(help="JUUUAAAAAAANNNNNNNNNNNNNNNNNNNNNNNNNN SOTOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO")
    async def soto(self, ctx):
        await ctx.send(file=discord.File(SOTO_PATH))
        await self.enqueue_filesystem_sound(ctx, SOTO_PARTY)

    @commands.command(aliases=["death", "nuke"], help="You need help.")
    @wade_or_collinses_only()
    async def surprise(self, ctx):
        await self.enqueue_filesystem_sound(ctx, SOTO_TINY_NUKE)
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        await asyncio.sleep(3)
        while self.get_now_playing(ctx.guild):
            await asyncio.sleep(0.2)
            print("Waiting to finish...")
        await voice.disconnect()

    @commands.command(help="GET MOBIUS HIS JET SKI")
    async def wow(self, ctx):
        await self.enqueue_filesystem_sound(ctx, WOW_PATH)

    @commands.command(help="Oh shoot.")
    async def ohshit(self, ctx):
        await self.enqueue_filesystem_sound(ctx, OHSHIT_PATH)

    @commands.command()
    async def gunter(self, ctx):
        await self.enqueue_filesystem_sound(ctx, GUNTER_PATH)

    @commands.command()
    async def gas(self, ctx):
        await self.enqueue_filesystem_sound(ctx, GASGASGAS_PATH)

    @commands.command()
    async def bill(self, ctx):
        await self.enqueue_filesystem_sound(ctx, BILLNYE_PATH)

    @commands.command(help="Yeah.")
    async def yeah(self, ctx):
        await self.enqueue_filesystem_sound(ctx, YEAH_PATH)

    @commands.command(help="He screams like a man.")
    async def goat(self, ctx):
        await self.enqueue_filesystem_sound(ctx, GOAT_SCREAM_PATH)

    @commands.command(help="Itsa me!")
    async def mario(self, ctx):
        await self.enqueue_filesystem_sound(ctx, SUPER_MARIO_PATH)

    @commands.command(name="home-depot", aliases=["hd"], help="How Doers Get More Done.")
    async def home_depot(self, ctx):
        await self.enqueue_filesystem_sound(ctx, HOME_DEPOT_PATH)

    @commands.command(help="Buuuhhhh.")
    async def buh(self, ctx):
        await self.enqueue_filesystem_sound(ctx, BUHH_PATH)

    @commands.command(aliases=["mb", "say"], help="Buuuhhhh.")
    async def moonbase(self, ctx, *song):

        lyrics = " ".join(song).replace("`", "")
        audio_file = tmp_fn("moonbase", ".mp3")

        log.debug(f"Compiling song: {lyrics}")

        tokens = moonbase.tokenize_string(lyrics)
        await ctx.send(f"Parsed {len(tokens)} literals.")
        notes, error = moonbase.translate(tokens)
        if error:
            await ctx.send(f"Woops: {error}")
            return
        if not notes:
            await ctx.send("Failed to produce any notes with that.")
            return
        tracks = moonbase.export_notes_to_moonbase(notes)
        if not tracks:
            await ctx.send("Failed to produce audio tracks from that.")
            return
        moonbase.compile_tracks(audio_file, *tracks)
        await self.enqueue_filesystem_sound(ctx, audio_file, volume=MOONBASE_VOLUME)

        # song = " ".join(song)
        # fn = tmp_fn("moonbase", "wav")
        # success, code, errstr = commit_moonbase(song, fn)
        # if not success:
        #     await ctx.send(f"Sorry, something went wrong (error code {code}).\n```{errstr}```")
        # await self.enqueue_filesystem_sound(ctx, fn, volume=MOONBASE_VOLUME)

    @commands.command(aliases=["youtube", "yt"], help="Play a YouTube video, maybe.")
    async def play(self, ctx, url):
        await ctx.message.add_reaction("👍")
        log.debug(f"Playing YouTube audio: {url}")
        results = youtube_to_audio_stream(url)
        if not results:
            await ctx.send("Failed to convert that link to something playable. Sorry about that.")
            return
        for info, stream_url in results:
            title = info["title"]
            # for k, v in info.items():
            #     print(f"======= {k}\n{v}")
            source = AudioSource()
            source.url = stream_url
            # await self.enqueue_audio(QueuedAudio(f"{title} (<{info['webpage_url']}>)", source, ctx, True))
            url = info["webpage_url"]
            print("====================\n\n\n==============")
            download_file(stream_url, "/tmp/youtube-audio.mp3")
            print("====================\n\n\n==============")
            qa = QueuedAudio(title, url, source, ctx, True)
            qa.volume = MUSIC_VOLUME
            await self.enqueue_audio(qa)
