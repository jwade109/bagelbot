#! /usr/bin/env python3

import sys
import os
from dataclasses import dataclass, field
from typing import List, Mapping, Tuple, Union
import re
from datetime import datetime, timedelta
from dateparser import parse as dateparse
import random
from fuzzywuzzy import fuzz
import warnings
from pytimeparse.timeparse import timeparse
from random import randint
 #from state_machine import get_param, set_param
from yaml import YAMLObject

import yaml # tmp
import logging

log = logging.getLogger("reminders")
log.setLevel(logging.DEBUG)


YAML_PATH = "/tmp/reminders.yaml"


# ignore dateparser warnings
warnings.filterwarnings("ignore",
    message="The localize method is no longer necessary, " \
    "as this time zone supports the fold attribute")


@dataclass(repr=True)
class Reminder(YAMLObject):
    yaml_tag = u'!Reminder'
    uid: int = field(default_factory=lambda: randint(0, 1E12))
    target: str = ""
    source: str = ""
    date: datetime = None
    task: str = ""
    repeat: timedelta = timedelta()
    completed: bool = False
    snoozed: timedelta = timedelta()

ReminderMap = Mapping[int, Reminder]

@dataclass(frozen=True, eq=True)
class RemindEvent:
    target: str = ""
    source: str = ""
    date: datetime = None
    task: str = ""


def get_reminder_event(rem: Reminder) -> RemindEvent:
    return RemindEvent(
        target=rem.target,
        source=rem.source,
        date=rem.date + rem.snoozed,
        task=rem.task
    )


def datestr(date: datetime) -> str:
    return date.strftime('%I:%M %p on %B %d, %Y')


def td_format(dt: timedelta):
    seconds = int(dt.total_seconds())
    periods = [
        ('year',        60*60*24*365),
        ('month',       60*60*24*30),
        ('day',         60*60*24),
        ('hour',        60*60),
        ('minute',      60),
        ('second',      1)
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds > period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            has_s = 's' if period_value > 1 else ''
            strings.append(f"{period_value} {period_name}{has_s}")
    return ", ".join(strings)


def reminder_msg(rem: RemindEvent, current_time: datetime) -> str:
    dstr = datestr(rem.date)
    sstr = rem.source
    if rem.source == rem.target:
        sstr = "you"
    agostr = "is right about now"
    if current_time - rem.date > timedelta(minutes=1):
        agostr = f"was {td_format(current_time - rem.date)} ago"
    return f"Hey {rem.target}, {sstr} asked me to remind you to " \
        f"\"{rem.task}\" at {dstr}, which {agostr}."


def parse_reminder_text(text: str, source: str, now: datetime) -> Reminder:
    ret = Reminder()
    repeat_pattern = r"(\s(on the daily|daily|every day|everyday|every (\d+) (days|minutes|hours)))"
    base_pattern = r"(.+?)\s(to\s)?(.*)\s((at|on|in|by)\b.+\b)"
    repeat_matches = re.search(repeat_pattern, text)
    if repeat_matches:
        td = timedelta(days=1)
        if repeat_matches.group(3) and repeat_matches.group(4):
            count = int(repeat_matches.group(3))
            unit = repeat_matches.group(4)
            td = timedelta(**{unit: count})
        ret.repeat = td
        text = re.sub(repeat_pattern, "", text, 1)
    matches = re.search(base_pattern, text)
    if not matches:
        log.debug("Doesn't match regex.")
        return None
    ret.target = matches.group(1)
    if ret.target == "me":
        ret.target = source
    ret.source = source
    ret.task = matches.group(3)
    datestr = matches.group(4)
    date = dateparse(datestr)
    if not date:
        log.debug(f"Unparseable date: {datestr}")
        return None
    if date < now:
        log.debug("Date is in the past.")
        return None
    ret.date = date
    return ret


@dataclass()
class SnoozeRequest:
    index: int = -1
    delta: timedelta = None
    until: datetime = None


def parse_snooze_request(text):
    pattern = r"snooze\s(\d+)\s(until|by|for)(\b.+\b)"
    matches = re.search(pattern, text)
    if not matches:
        log.debug("Snooze request doesn't match regex.")
        return None
    sr = SnoozeRequest()
    sr.index = int(matches.group(1))
    sr.delta = timeparse(matches.group(3))
    if sr.delta is None:
        sr.until = dateparse(matches.group(3))
        if not sr.until:
            log.debug("Bad timedelta string.")
            return None
    else:
        sr.delta = timedelta(seconds=sr.delta)
    return sr


def do_snooze(reminders: ReminderMap, text: str, agent_name: str):
    sr = parse_snooze_request(text)
    if not sr:
        return
    uids = get_agent_tasks(reminders, agent_name)
    if sr.index > len(uids):
        log.debug("Index provided is greater the number of reminders you have.")
        return
    rem = reminders[uids[sr.index - 1]] # remember, humans use 1-indexing
    if sr.delta is not None:
        log.debug(f"Delay task {rem.task} by {sr.delta}.")
        delta = sr.delta
        rem.snoozed += delta
    elif sr.until is not None:
        if sr.until < rem.date:
            log.debug("Cannot snooze until a date before the reminder date.")
            return
        log.debug(f"Delay task {rem.task} until {sr.until}.")
        delta = sr.until - rem.date
        rem.snoozed += delta
    else:
        log.debug(f"Bad snooze request: {sr}")
        return
    rem.completed = False
    add_or_update_reminder(reminders, rem)


def do_delete(reminders: ReminderMap, index: int, agent_name: str):
    uids = get_agent_tasks(reminders, agent_name)
    if index > len(uids):
        log.debug("Index provided is greater the number of reminders you have.")
        return
    uid_to_delete = uids[index - 1] # humans are one-indexed
    if uid_to_delete not in reminders:
        log.debug(f"UID {uid_to_delete} not in reminders!")
    rem = reminders[uid_to_delete]
    del reminders[uid_to_delete]
    log.debug(f"Deleted task \"{rem.task}\".")


def sort_by_date(reminders: List[Reminder]) -> List[Reminder]:
    return sorted(reminders, key=lambda r: (r.completed, r.date + r.snoozed))


def print_reminders(reminders: List[Reminder]):
    for i, rem in enumerate(reminders):
        time = rem.date + rem.snoozed
        nrt = "completed" if rem.completed else datestr(time)
        repeatstr = " (every " + td_format(rem.repeat) + ")" if rem.repeat else ""
        snoozestr = ""
        if rem.snoozed:
            snoozestr = f" (snoozed {td_format(rem.snoozed)})"
        istr = f"[{i+1}]"
        route = f"{istr:6} from {rem.source} to {rem.target}:"
        log.debug(f"{rem.uid:<14}{route:30s}{nrt:30s}{rem.task}{repeatstr}{snoozestr}")


def find_task(search, reminders):
    results = []
    for rem in reminders:
        r = fuzz.ratio(search, rem.task)
        results.append((r, rem))
    results.sort(key=lambda r: -r[0]) # sort so the best match is first
    return results


def is_relevant_to(rem: Reminder, agent_name: str) -> bool:
    if not agent_name:
        return False
    if agent_name == "~": # backdoor
        return True
    return rem.source == agent_name or rem.target == agent_name


def is_directed_at(rem: Reminder, agent_name: str) -> bool:
    if not agent_name:
        return False
    if agent_name == "~": # backdoor
        return True
    return rem.target == agent_name


def get_relevant_tasks(reminders: ReminderMap, agent_name: str) -> List[int]:
    reminders = [r for r in reminders.values() if is_relevant_to(r, agent_name)]
    return [r.uid for r in sort_by_date(reminders)]


def get_agent_tasks(reminders: ReminderMap, agent_name: str) -> List[int]:
    reminders = [r for r in reminders.values() if is_directed_at(r, agent_name)]
    return [r.uid for r in sort_by_date(reminders)]


# if the reminder is single-fire, marks complete;
# otherwise, advances the timestamp to the next future date
def mark_complete_or_advance(rem: Reminder, now: datetime):
    if not rem.repeat:
        rem.completed = True
        return
    while rem.date <= now:
        rem.date += rem.repeat
        rem.snoozed = timedelta()


def spin_until(reminders: ReminderMap, current_time: datetime) -> List[RemindEvent]:
    events = []
    for rem in reminders.values():
        if rem.completed:
            continue
        time = rem.date + rem.snoozed
        if time <= current_time:
            events.append(get_reminder_event(rem))
            mark_complete_or_advance(rem, current_time)
    return events


def add_or_update_reminder(reminders: ReminderMap, rem: Reminder):
    reminders[rem.uid] = rem


def main():

    def log_in_as():
        print(" username > ", end="")
        sys.stdout.flush()
        return input() or "~"


    REMINDERS = {}
    NOW = datetime.now()
    SPIN_RESOLUTION = timedelta(minutes=1)
    logged_in_as = log_in_as()


    PHRASES = [
        "me to do the dishes at 5 pm every day",
        "me to do the dishes by tomorrow",
        "me daily to scream at the moon in 1 hour",
        "John to do the dishes every day at 7:30 pm",
        "Paul to do my homework in 4 days",
        "John view the quadrantids meteor shower on January 2, 2024, 1 am",
        "Paul eat a krabby patty at 3 am tomorrow",
        "me to brush my teeth every 8 hours in 3 hours",
        "Sally to do the do at 12 pm tomorrow",
        "Sally to get gud in 3 minutes"
    ]

    for phrase in PHRASES:
        rem = parse_reminder_text(phrase, logged_in_as, NOW)
        if not rem:
            print(f"Bad rem phrase: {phrase}")
        add_or_update_reminder(REMINDERS, rem)

    while True:

        # set_param("reminders", REMINDERS, YAML_PATH)
        print(f"\n [{logged_in_as}] [{datestr(NOW)}] $ bb remind ", end="");
        sys.stdout.flush();
        text = input()


        lines, edict = process_text_input(text, logged_in_as)
        for line in lines:
            print(line)
        if edict:
            print(edict)

        continue

        if not text:
            text = "spin"
        args = text.split(" ")

        if args[0] in ["c", "clear"]:
            os.system("cls")
            continue
        if args[0] == "list":
            uids = get_agent_tasks(REMINDERS, logged_in_as)
            print_reminders([REMINDERS[uid] for uid in uids])
            continue
        if args[0] == "snooze":
            do_snooze(REMINDERS, text, logged_in_as)
            continue
        if args[0] == "delete":
            if len(args) < 2:
                print("Requires an index to delete.")
            index = int(args[1])
            do_delete(REMINDERS, index, logged_in_as)
            continue
        if args[0] == "spin":
            rems = []
            while not rems:
                NOW += SPIN_RESOLUTION
                if not any(r for r in REMINDERS.values() if not r.completed):
                    print("No pending reminders remain.")
                    break
                rems = spin_until(REMINDERS, NOW)
                for r in rems:
                    print(reminder_msg(r, NOW))
            continue
        if args[0] == "login":
            logged_in_as = args[1]
            continue
        if args[0] in ["e", "exit"]:
            return 0


        # parsing HAS to use real-time now, not sim-time now,
        # since the parsing library I'm using uses the wall clock
        # and has no facilities for simulating the passage of time
        rem = parse_reminder_text(text, logged_in_as, datetime.now())
        if rem:
            print(rem)
            add_or_update_reminder(REMINDERS, rem)



import discord
from discord.ext import commands, tasks


def reminder_to_embed(rem: Reminder):
    embed = discord.Embed(title=rem.task, description="Reminder", color=0x3498db)
    embed.add_field(name="Date", value=datestr(rem.date), inline=False)
    if rem.repeat:
        embed.add_field(name="Repeats", value=td_format(rem.repeat), inline=False)
    if rem.source != rem.target:
        embed.add_field(name="Source", value=rem.source, inline=True)
    embed.add_field(name="Reminding", value=rem.target, inline=True)
    return embed


def remind_event_to_embed(rem: RemindEvent):
    embed = discord.Embed(title=f"It's time to {rem.task}!", color=0x3498db)
    embed.add_field(name="Date", value=datestr(rem.date), inline=False)
    if rem.source != rem.target:
        embed.add_field(name="Source", value=rem.source, inline=True)
    embed.add_field(name="Reminding", value=rem.target, inline=True)
    return embed


def reminders_to_embed(reminders: List[Reminder], title="", desc=""):
    embed = discord.Embed(title=title if title else "Reminders List",
        description=desc, color=0x45FF23)
    is_first_row = True

    def to_column(func):
        return "\n".join(func(rem) for rem in reminders)

    def task_str(rem):
        return rem.task + (" (Completed)" if rem.completed else "")

    def date_str(rem):
        return datestr(rem.date)

    def repeats_str(rem):
        return f"every {td_format(rem.repeat)}" if rem.repeat else "-"

    embed.add_field(name="Task", value=to_column(task_str), inline=True)
    embed.add_field(name="Date", value=to_column(date_str), inline=True)
    embed.add_field(name="Repeats", value=to_column(repeats_str), inline=True)
    return embed


async def fetch_from_mention(client, mention: str):
    regex = r"<([#@])(\d{18})>"
    match = re.search(regex, mention)
    if not match:
        return None
    is_person = match.group(1) == '@'
    uid = int(match.group(2))
    messagable = await client.fetch_user(uid) if \
        is_person else client.get_channel(uid)
    return messagable


async def fetch_reminder_endpoints(client, rem: Union[Reminder, RemindEvent]):
    s = await fetch_from_mention(client, rem.source)
    if rem.source == rem.target:
        return s, s
    t = await fetch_from_mention(client, rem.target)
    return s, t


DONT_ALERT_USERS = discord.AllowedMentions(users=False)


class RemindV2(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.reminders = {}
        self.process_reminders_v2.start()

    @tasks.loop(seconds=5)
    async def process_reminders_v2(self):
        now = datetime.now()
        triggered_reminders = spin_until(self.reminders, now)
        if not triggered_reminders:
            return
        for event in triggered_reminders:
            log.info(f"Triggered now: {event}")

            source, target = await fetch_reminder_endpoints(self.bot, event)
            embed = remind_event_to_embed(event)
            am = discord.AllowedMentions(users=False)

            if event.source == event.target:
                await target.send(f"Hey, {event.target}, you asked me to "
                    "remind you about this.", embed=embed, allowed_mentions=DONT_ALERT_USERS)
            else:
                await source.send(f"Hey, {event.source}, your reminder to "
                    f"{event.target} just went through.", embed=embed, allowed_mentions=DONT_ALERT_USERS)
                await target.send(f"Hey, {event.target}, a reminder from "
                    f"{event.source} has arrived.", embed=embed, allowed_mentions=DONT_ALERT_USERS)

    @commands.command(aliases=["remind", "r2"])
    async def remind2(self, ctx, *args):
        if not args:
            await ctx.send("Requires text input.")
            return
        whoami = str(ctx.message.author.mention)
        text = " ".join(args)
        now = datetime.now()
        log.debug(f"{ctx.message.author} AKA {whoami}: {text}")
        rem = parse_reminder_text(text, whoami, now)
        if rem:

            source, target = await fetch_reminder_endpoints(self.bot, rem)

            if not source:
                await ctx.send("Hmm, looks like this isn't a valid "
                    f"source: {rem.source}", allowed_mentions=DONT_ALERT_USERS)
                return
            if not target:
                await ctx.send("Hmm, looks like this isn't a valid "
                    f"target: {rem.target}", allowed_mentions=DONT_ALERT_USERS)
                return

            log.debug(f"Adding this reminder to database: {rem}")
            add_or_update_reminder(self.reminders, rem)
            embed = reminder_to_embed(rem)
            you = "you" if rem.source == rem.target else rem.target
            await ctx.send(f"Ok, I'll do my best to remind {you} at "
                "the appropriate time.", embed=embed, allowed_mentions=DONT_ALERT_USERS)
            return

        command_name = args[0]
        log.debug(f"Command name: {command_name}")
        if command_name == "list":
            uids = get_agent_tasks(self.reminders, whoami)
            if not uids:
                await ctx.send("You have no reminders.")
                return
            rems = [self.reminders[uid] for uid in uids]
            embed = reminders_to_embed(rems, "Reminder List", f"{whoami}'s Reminders")
            await ctx.send("Found these reminders.", embed=embed)

        else:
            await ctx.send("Sorry, I couldn't understand that.")



if __name__ == "__main__":
    main()








