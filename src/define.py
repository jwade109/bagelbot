#! /usr/bin/python3

import sys
from dataclasses import dataclass, field
from typing import List
import wikipediaapi
import yaml
import re
from wiktionaryparser import WiktionaryParser
from bs4 import BeautifulSoup
import requests
import logging
import random
from datetime import datetime
from dateutil import parser as timeparser
import googlesearch


wiktionary = WiktionaryParser()
wikipedia = wikipediaapi.Wikipedia('en',
    extract_format=wikipediaapi.ExtractFormat.WIKI)


log = logging.getLogger("define")
log.setLevel(logging.DEBUG)


@dataclass()
class Definition:
    word: str = ""
    part_of_speech: str = ""
    tense_summary: str = ""
    definitions: List[str] = field(default_factory=list)


@dataclass()
class UrbanDefinition:
    word: str = ""
    author: str = ""
    definition: str = ""
    example: str = ""
    thumbs_up: int = 0
    thumbs_down: int = 0
    timestamp: datetime = None
    url: str = ""


@dataclass()
class GoogleResult:
    search: str = ""
    results: List[str] = None


def do_wiktionary(word) -> List[Definition]:
    defined = wiktionary.fetch(word)
    if not defined:
        return []
    results = []
    for entry in defined:
        # print("======")
        # print(entry.keys())
        definitions = entry["definitions"]
        # print(f"{len(definitions)} definitions.")
        for definition in definitions:
            # print(yaml.dump(definition))
            d = Definition()
            d.word = word # perhaps unnecessary
            d.part_of_speech = definition["partOfSpeech"]
            d.tense_summary = definition["text"][0]
            d.definitions = definition["text"][1:]
            results.append(d)
    return results


def crop_text_nicely(text: str, n_characters: int) -> str:
    sentences = text.split(" ")
    running_sum = 0
    dotdotdot = False
    to_join = []
    for sentence in sentences:
        running_sum += len(sentence)
        if running_sum + 3 > n_characters:
            dotdotdot = True
            break
        to_join.append(sentence)
    return " ".join(to_join) + ("..." if dotdotdot else "")


@dataclass()
class WikiPage:
    title: str = ""
    url:   str = ""
    text:  str = ""
    is_referral: bool = False
    is_stub:     bool = False
    is_math:     bool = False


def pretty_print_wikipage(w: WikiPage):
    print(f"{w.title} -- {w.url} -- {w.is_math}\n")
    s = crop_text_nicely(w.text, 400)
    print(s)


def do_wikipedia(word):
    page = wikipedia.page(word)
    if not page.exists():
        return None

    ret = WikiPage()
    ret.is_stub = len(page.summary) < 150
    ret.is_referral = "may refer to" in page.summary or "may also refer to" in page.summary
    # print(f"{page.title} -- {page.fullurl} {'WEIRD' if (is_stub or is_referral) else ''}")
    s = page.text if (ret.is_stub or ret.is_referral) else page.summary
    ret.is_math = "\displaystyle" in s
    s = s.replace("(, ", "(").replace(" )", ")") \
         .replace("(; ", "(").replace("() ", "") \
         .replace("(), ", "")
    if ret.is_referral:
        s = "\n~ ".join([x for x in s.split("\n") if x])
    else:
        s = "\n\n".join([x for x in s.split("\n") if x])

    if ret.is_math:
        log.debug(f"This page is a math page: {page.fullurl}")

    s = crop_text_nicely(s, 400)
    ret.text = s
    ret.title = page.title
    ret.url = page.fullurl
    return ret


def do_google(word):
    try:
        res = GoogleResult()
        res.search = word
        res.results = list(googlesearch.search(word, num=3, stop=3))
        return res
    except Exception as e:
        print(e)
        return None


def get_best_available_definition(word):
    wikidefs = do_wiktionary(word)
    if wikidefs:
        return wikidefs
    wikipage = do_wikipedia(word)
    if wikipage and not wikipage.is_referral and not wikipage.is_math:
        return wikipage
    urban = get_urban_definition(word)
    if urban:
        return urban
    goog = do_google(word)
    if goog:
        return goog
    return None


def scrub_brackets_from_text(text):
    return re.sub(f"\[(.+?)\]", r"\1", text) # .replace("\n", "").replace("\r", "")


def get_urban_definition(word):
    response = requests.get(f"http://api.urbandictionary.com/v0/define?term={word}")
    json = response.json()
    if not json or "list" not in json:
        return None
    results = []
    for thing in response.json()["list"]:
        ud = UrbanDefinition()
        ud.word = thing["word"]
        ud.author = thing["author"]
        ud.definition = scrub_brackets_from_text(thing["definition"])
        ud.example = scrub_brackets_from_text(thing["example"])
        ud.thumbs_up = thing["thumbs_up"]
        ud.thumbs_down = thing["thumbs_down"]
        ud.timestamp = timeparser.parse(thing["written_on"])
        ud.url = thing["permalink"]
        results.append(ud)
    if not results:
        return None
    results.sort(key=lambda x: x.thumbs_down - x.thumbs_up)
    return results[0]


def main():
    word = " ".join(sys.argv[1:])
    if not word:
        print("Need a word.")
        return 1

    print(get_best_available_definition(word))


if __name__ == "__main__":
    main()


import discord
from discord.ext import commands, tasks


WIKTIONARY_URL = "https://en.wiktionary.org/wiki"


def wikipage_to_embed(page: WikiPage):
    embed = discord.Embed(title=page.title,
        description=page.text, url=page.url)
    embed.set_footer(text=page.url)
    return embed


def definition_to_embed(d: Definition):
    embed = discord.Embed(title=f"{d.word.capitalize()}")
    embed.add_field(name=d.part_of_speech,
        value="\n".join(f"- {x}" for x in d.definitions), inline=False)
    embed.set_footer(text="Courtesy of Wiktionary")
    return embed


def urban_def_to_embed(ud: UrbanDefinition):
    embed = discord.Embed(title=f"{ud.word}",
        description=ud.definition, url=ud.url)
    if ud.example:
        embed.add_field(name="Example", value=ud.example, inline=False)
    embed.set_footer(text="Courtesy of UrbanDictionary contributor "
        f"{ud.author}")
    return embed


def google_to_embed(g: GoogleResult):
    embed = discord.Embed(title=f"Search results for \"{g.search}\"",
        description="\n".join(g.results))
    return embed


def definitions_to_embed(ds: List[Definition]):
    if not ds:
        return None
    first = ds[0]
    # url = f"{WIKTIONARY_URL}/{first.word}"
    embed = discord.Embed(title=f"{first.word.capitalize()}")
    for d in ds:
        defs = d.definitions[:min(2, len(d.definitions))]
        embed.add_field(name=d.part_of_speech,
            value="\n".join(f"- {x}" for x in defs), inline=False)
    embed.set_footer(text="Courtesy of Wiktionary")
    return embed


def any_definition_to_embed(anydef):
    if not anydef:
        return None
    if isinstance(anydef, WikiPage):
        return wikipage_to_embed(anydef)
    if isinstance(anydef, UrbanDefinition):
        return urban_def_to_embed(anydef)
    if isinstance(anydef, GoogleResult):
        return google_to_embed(anydef)
    if len(anydef) > 1:
        return definitions_to_embed(anydef)
    return definition_to_embed(anydef[0])


class Define(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def urbandict(self, ctx, *search):
        phrase = " ".join(search)
        if not phrase:
            await ctx.send("Requires a word or phrase to look up.")
            return
        urban = get_urban_definition(phrase)
        if not urban:
            await ctx.send("Sorry, I couldn't find an Urban Dictionary " \
                f"entry for \"{phrase}\".")
            return
        embed = urban_def_to_embed(urban)
        await ctx.send(f"Found this Urban Dictionary entry for \"{phrase}\".", embed=embed)

    @commands.command()
    async def wiktionary(self, ctx, *search):
        phrase = " ".join(search)
        if not phrase:
            await ctx.send("Requires a word or phrase to look up.")
            return
        res = do_wiktionary(phrase)
        if not res:
            await ctx.send("Sorry, I couldn't find a Wiktionary " \
                f"entry for \"{phrase}\".")
            return

        if len(res) > 1:
            embed = definitions_to_embed(res)
            await ctx.send(f"Found these definitions for \"{phrase}\".", embed=embed)
        else:
            embed = definition_to_embed(res[0])
            await ctx.send(f"Found this definition for \"{phrase}\".", embed=embed)

    @commands.command()
    async def wikipedia(self, ctx, *search):
        phrase = " ".join(search)
        if not phrase:
            await ctx.send("Requires a word or phrase to look up.")
            return
        res = do_wikipedia(phrase)
        if not res:
            await ctx.send("Sorry, I couldn't find a Wikipedia " \
                f"entry for \"{phrase}\".")
            return
        embed = wikipage_to_embed(res)
        await ctx.send(f"Found this Wikipedia entry for \"{phrase}\".", embed=embed)

    @commands.command()
    async def google(self, ctx, *search):
        phrase = " ".join(search)
        if not phrase:
            await ctx.send("Requires a word or phrase to look up.")
            return
        res = do_google(phrase)
        if not res:
            await ctx.send("Sorry, even Google doesn't know what that means.")
            return
        embed = google_to_embed(res)
        await ctx.send(f"Got these Google results for \"{phrase}\".", embed=embed)

    @commands.command()
    async def define(self, ctx, *search):
        phrase = " ".join(search)
        if not phrase:
            await ctx.send("Requires a word or phrase to look up.")
            return
        res = get_best_available_definition(phrase)
        log.debug(f"For \"{phrase}\", got these definitions: {res}")
        if not res:
            await ctx.send(f"Sorry, I couldn't find any results for \"{phrase}\".")
            return
        if isinstance(res, WikiPage):
            embed = wikipage_to_embed(res)
            await ctx.send(f"Found this Wikipedia entry for \"{phrase}\".", embed=embed)
            return
        elif isinstance(res, UrbanDefinition):
            embed = urban_def_to_embed(res)
            await ctx.send(f"Found this Urban Dictionary entry for \"{phrase}\".", embed=embed)
            return
        elif isinstance(res, GoogleResult):
            embed = google_to_embed(res)
            await ctx.send(f"Found these Google results for \"{phrase}\".", embed=embed)
            return

        if len(res) > 1:
            embed = definitions_to_embed(res)
            await ctx.send(f"Found these definitions for \"{phrase}\".", embed=embed)
        else:
            embed = definition_to_embed(res[0])
            await ctx.send(f"Found this definition for \"{phrase}\".", embed=embed)
