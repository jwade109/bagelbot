import discord
from discord.ext import commands
from resource_paths import *
from state_machine import get_param, set_param
from bblog import log
import random
import re
import calendar
from glob import glob
import giphy
from resource_paths import tmp_fn
from gritty import do_gritty
from typing import Union
from cowpy import cow
import pypokedex
import requests


class Miscellaneous(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Get the current time.")
    async def time(self, ctx):
        await ctx.send("It's Hubble Time.")

    @commands.command(aliases=["badmath"], help="Perform mathy math on two numbers.")
    async def math(self, ctx, a: Union[int, float], op: str, b: Union[int, float]):
        s = 0
        if op == "+":
            s = a + b
        elif op == "-":
            s = a - b
        elif op == "*":
            s = a * b
        elif op == "/":
            s = a / b
        else:
            await ctx.send(f"Error: '{op}' is not a supported math operator.")
            return
        if isinstance(s, int):
            s *= (random.randint(95, 105) / 100)
            s = int(round(s))
        else:
            s *= (random.randint(95, 105) / 100)

        def fmt(num):
            if isinstance(num, int):
                return str(num)
            return f"{num:0.3f}"

        await ctx.send(f"{fmt(a)} {op} {fmt(b)} = {fmt(s)}")

    @commands.command(help="Use a moose to express your thoughts.")
    async def moose(self, ctx, *message):
        cheese = cow.Moose()
        msg = cheese.milk(" ".join(message))
        await ctx.send(f"```\n{msg}\n```")

    @commands.command(help="Roll a 20-sided die.")
    async def d20(self, ctx):
        roll = random.randint(1, 20)
        if roll == 20:
            await ctx.send(f"Rolled a 20! :confetti_ball:")
        else:
            await ctx.send(f"Rolled a {roll}.")

    @commands.command(help="Say hi!")
    async def hello(self, ctx):
        await ctx.send(f"Hey, {ctx.author.name}, it me, ur bagel.")

    @commands.command(help="Get info about a Pokemon.")
    async def pokedex(self, ctx, id_or_name: Union[int, str] = None):
        if id_or_name is None:
            id_or_name = random.randint(1, 898)

        if isinstance(id_or_name, str):
            try:
                p = pypokedex.get(name=id_or_name)
            except Exception as e:
                log.error(e)
                await ctx.send(f"Pokemon \"{id_or_name}\" was not found.")
                return
        else:
            try:
                p = pypokedex.get(dex=id_or_name)
            except Exception as e:
                log.error(e)
                await ctx.send(f"Pokemon #{id_or_name} was not found.")
                return

        embed = discord.Embed()
        embed.title = f"#{p.dex}: {p.name.capitalize()}"
        embed.description = f"{', '.join([x.capitalize() for x in p.types])} type. " \
            f"{p.weight/10} kg. {p.height/10} m."
        embed.set_image(url="https://assets.pokemon.com/assets/" \
            f"cms2/img/pokedex/detail/{str(p.dex).zfill(3)}.png")
        await ctx.send(embed=embed)

    @commands.command(help="Drop some hot Bill Watterson knowledge.")
    async def ch(self, ctx):
        files = [os.path.join(path, filename)
                 for path, dirs, files in os.walk(CH_DIRECTORY)
                 for filename in files
                 if filename.endswith(".gif")]
        choice = random.choice(files)
        result = re.search(r".+(\d{4})(\d{2})(\d{2}).gif", choice)
        year = int(result.group(1))
        month = int(result.group(2))
        day = int(result.group(3))
        message = f"{calendar.month_name[month]} {day}, {year}."
        await ctx.send(message, file=discord.File(choice))

    @commands.command(help="A webcomic of romance, sarcasm, math, and language.")
    async def xkcd(self, ctx, num: int = None):
        path = "" if num is None else str(num)
        r = requests.get(f"https://xkcd.com/{path}/info.0.json")
        data = r.json()
        log.debug(data)
        embed = discord.Embed()
        embed.title = data["title"]
        embed.set_image(url=data["img"])
        await ctx.send(embed=embed)

    @commands.command(help="Record that funny thing someone said that one time.")
    async def quote(self, ctx, user: discord.User = None, *message):
        quotes = get_param(f"{ctx.guild}_quotes", [])
        if user and not message:
            await ctx.send("Good try! I can't record an empty quote, though.")
            return
        if message:
            quotes.append({"msg": " ".join(message), "author": user.name, "quoted": 0})
            set_param(f"{ctx.guild}_quotes", quotes)
            await ctx.send(f"{user.name} has been recorded for posterity.")
            return
        if not quotes:
            await ctx.send("No quotes! Record a quote using this command.")
            return
        num_quoted = [x["quoted"] for x in quotes]
        qmin = min(num_quoted)
        qmax = max(num_quoted)
        if qmin == qmax:
            w = num_quoted
        else:
            w = [1 - (x - qmin) / (qmax - qmin) + 0.5 for x in num_quoted]

        if len(w) == 1 and w[0] == 0: # TODO better weighting scheme
            w[0] = 1

        i = random.choices(range(len(quotes)), weights=w, k=1)[0]
        author = quotes[i]["author"]
        msg = quotes[i]["msg"]
        quotes[i]["quoted"] += 1
        set_param(f"{ctx.guild}_quotes", quotes)
        num_quoted = [x["quoted"] for x in quotes]
        await ctx.send(f"\"{msg}\" - {author}")

    @commands.command(help="Add some anti-fascism to pictures of you and your friends!")
    async def gritty(self, ctx, *options):
        log.debug(f"{ctx.message.author} wants to be gritty, opts={options}.")
        if not ctx.message.attachments:
            await ctx.send("Please attach at least one image to add Gritty to.")
            return

        opts = {}
        for o in options:
            try:
                if "=" not in o:
                    await ctx.send(f"Malformed parameter: `{o}`. Parameters look like `key=value`.")
                    return
                k, v = o.split("=")
                if v.isdigit():
                    opts[k] = int(v)
                else:
                    opts[k] = float(v)
            except:
                await ctx.send(f"Malformed parameter: `{o}`. Parameters look like `key=value`.")
                return

        invalid_keys = [x for x in opts.keys() if x not in ["scale", "neighbors", "size"]]
        if invalid_keys:
            invalid_keys = [f'`{x}`' for x in invalid_keys]
            await ctx.send(f"These parameters are invalid: {' '.join(invalid_keys)}. " \
                f"Valid keys are `scale`, `neighbors`, and `size`.")
            return

        log.debug(f"Successfully parsed options: {opts}.")

        images_to_process = []

        for att in ctx.message.attachments:
            dl_filename = tmp_fn("gritty", att.filename.lower())
            if any(dl_filename.endswith(image) for image in ["png", "jpeg", "gif", "jpg"]):
                log.debug(f"Saving image attachment to {dl_filename}")
                await att.save(dl_filename)
                images_to_process.append(dl_filename)
            else:
                log.warning(f"Not saving attachment of unsupported type: {dl_filename}.")
                dl_filename = None

        if not images_to_process:
            await ctx.send("No image attachments found. This command can only operate on images.")
            return

        for img_path in images_to_process:
            out_path = stamped_fn("gritty", "jpg")
            if do_gritty(img_path, out_path, opts):
                await ctx.send(file=discord.File(out_path))
            else:
                await ctx.send("Hmm, I couldn't find any faces in this image.")

    @commands.command(help="Get a GIF.")
    async def gif(self, ctx, *to_translate):
        if not to_translate:
            log.debug(f"{ctx.message.author} wants a GIF.")
            url = giphy.random("bagels")
            await ctx.send(url)
            return
        to_translate = " ".join(to_translate)
        log.debug(f"{ctx.message.author} wants a GIF for message {to_translate}.")
        url = giphy.translate(to_translate)
        log.debug(f"Choice is {url}.")
        await ctx.send(url)

    @commands.command(help="Get a dog picture.")
    async def dog(self, ctx):
        log.debug(f"Delivering a dog picture.")
        files = glob(f"{DOG_PICS_DIR}/*.jpg")
        if not files:
            log.error(f"No files to choose from in {DOG_PICS_DIR}.")
            await ctx.send("Woops, I couldn't find any dog pics to show you. This is an error.")
            return
        choice = random.choice(files)
        log.debug(f"choice: {choice}")
        await ctx.send(file=discord.File(choice))
