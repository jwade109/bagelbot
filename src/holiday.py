#! /usr/bin/env python3

import requests
import dateutil.rrule as rr
from datetime import datetime, timedelta
import random
import re
import logging
from bs4 import BeautifulSoup

from define import get_best_available_definition, any_definition_to_embed
from state_machine import get_param, set_param
from ws_dir import WORKSPACE_DIRECTORY

import discord
from discord.ext import commands, tasks


DONT_ALERT_USERS = discord.AllowedMentions(users=False)


log = logging.getLogger("holidays")
log.setLevel(logging.DEBUG)


def parse_holiday_title_region(s):
    result = re.search(r"(.+) in (.*)", s)
    if result:
        return result.group(1), result.group(2)
    return s, ""


def get_holidays_on_day(dt: datetime):
    r = requests.get("https://national-api-day.herokuapp.com/" \
        f"api/date/{dt.month}/{dt.day}")
    return r.json()["holidays"]


def get_holidays_in_month(month):
    r = requests.get("https://national-api-day.herokuapp.com/" \
        f"api/month/{month}")
    return r.json()["holidays"]


def get_random_holiday_on_day(dt: datetime):
    return random.choice(get_holidays_on_day(dt))


def get_better_holidays_today():
    r = requests.get("https://nationaldaycalendar.com/what-day-is-it/")
    soup = BeautifulSoup(r.text, 'html.parser')
    # maybe will need to improve this rule in the future,
    # and it's also extremely fragile -- if the site changes its html
    # structure at all, we're completely boned
    return [item.text for item in soup.find_all("span", itemprop="name")]


def get_better_random_holiday_today():
    return random.choice(get_better_holidays_today())


RECURRENCE_RULE = rr.rrule(freq=rr.DAILY, interval=1,
    dtstart=datetime.now().replace(hour=11, minute=0, second=0, microsecond=0))


YAML_PATH = WORKSPACE_DIRECTORY + "/private/holidays.yaml"


class Holidays(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.next_fire = None
        self.subscribers = get_param("subscribers", {}, YAML_PATH)


    @commands.Cog.listener()
    async def on_ready(self):
        self.holiday_alerts_loop.start()

    async def fire_holiday_alerts(self):
        now = datetime.now()
        nxt = RECURRENCE_RULE.after(now)
        if not self.next_fire:
            log.debug(f"Next holiday alert at {nxt}.")
            self.next_fire = nxt
        if nxt == self.next_fire:
            return
        log.info(f"Scheduled holiday alerts at {self.next_fire} triggered now; next is {nxt}.")
        self.next_fire = nxt
        log.debug(self.subscribers)

        h = get_better_random_holiday_today()
        t, _ = parse_holiday_title_region(h)
        d = get_best_available_definition(t)
        e = any_definition_to_embed(d)

        datestr = datetime.strftime(now, "%B %d, %Y")

        # fix problem with change of size during iteration?
        subscribers = list(self.subscribers.items())
        for uid, info in subscribers:
            kind = info["type"]
            if kind == "user":
                user = await self.bot.fetch_user(uid)
            elif kind == "channel":
                user = await self.bot.fetch_channel(uid)
            msg = f"Hey {user.mention}, today ({datestr}) is **{h}**!"
            if e:
                msg += "\n\nI found some info online about this holiday."
            await user.send(msg, embed=e, allowed_mentions=DONT_ALERT_USERS)

    @tasks.loop(seconds=10)
    async def holiday_alerts_loop(self):
        try:
            await self.fire_holiday_alerts()
        except Exception as e:
            print(f"Exception in holiday alerts loop: {e}")
            log.error(f"Exception in holiday alerts loop: {e}")

    @commands.command(name="holiday-subscribe", aliases=["hsub"])
    async def holiday_subscribe(self, ctx, text_channel: discord.TextChannel = None):

        target = ctx.author
        kind = "user"
        if text_channel:
            target = text_channel
            kind = "channel"

        if target.id in self.subscribers:
            await ctx.send(f"{target.mention} is already a subscriber to " \
                "daily holiday alerts.", allowed_mentions=DONT_ALERT_USERS)
            return

        self.subscribers[target.id] = {
            "name": str(target),
            "type": kind
        }

        set_param("subscribers", self.subscribers, YAML_PATH)
        await ctx.send(f"{target.mention} is now subscribed to daily " \
            "holiday alerts.", allowed_mentions=DONT_ALERT_USERS)


    @commands.command(name="holiday-unsubscribe", aliases=["hunsub"])
    async def holiday_unsubscribe(self, ctx, text_channel: discord.TextChannel = None):

        target = ctx.author
        if text_channel:
            target = text_channel

        if not target.id in self.subscribers:
            await ctx.send(f"{target.mention} isn't a subscriber to daily holiday alerts.",
                allowed_mentions=DONT_ALERT_USERS)
            return
        log.info(f"Unsubscribing user {self.subscribers[target.id]}.")
        del self.subscribers[target.id]
        set_param("subscribers", self.subscribers, YAML_PATH)
        await ctx.send(f"{target.mention}'s subscription to daily holiday " \
            "alerts has been terminated.", allowed_mentions=DONT_ALERT_USERS)


def main():

    h = get_better_random_holiday_today()
    print(h)
    t, _ = parse_holiday_title_region(h)
    print(t)
    d = get_best_available_definition(t)
    print(d)
    pass


if __name__ == "__main__":
    main()
