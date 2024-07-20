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
from state_machine import get_param, set_param
from yaml import YAMLObject
from ws_dir import WORKSPACE_DIRECTORY
from bot_common import DONT_ALERT_USERS
from bagelshop.logging import log
import socket


YAML_PATH = WORKSPACE_DIRECTORY + "/private/reminders.yaml"


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


def td_format(dt: timedelta, stop_unit=None):
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
            if stop_unit and stop_unit == period_name:
                break
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


# if the user doesn't provide a time but DOES provide a repeat duration,
# default the time of next event to NOW + REPEAT DURATION
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
        log.debug(f"For date string {datestr}, generated date is in the past: {date}")
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
            uids = get_relevant_tasks(REMINDERS, logged_in_as)
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


NICE_MILD_BLUE = 0x5b56e3
NICE_MILD_RED = 0xe85e3f
NICE_MILD_GREEN = 0x52d969


def reminder_to_embed(rem: Reminder):
    tstr = datestr(rem.date)
    if rem.snoozed:
        tstr += f" (snoozed {td_format(rem.snoozed)})"
    desc = f"When: {tstr}\nWho: {rem.target}"
    embed = discord.Embed(title=f"Reminder: {rem.task}",
        description=desc, color=NICE_MILD_RED)
    if rem.repeat:
        embed.add_field(name="Repeats", value=f"every {td_format(rem.repeat)}", inline=True)
    return embed


def remind_event_to_embed(rem: RemindEvent):
    embed = discord.Embed(title=f"It's time to {rem.task}!", color=NICE_MILD_GREEN)
    return embed


def reminders_to_embeds(reminders: List[Reminder], reminders_per_embed=15):

    now = datetime.now()
    embeds = []
    embed = discord.Embed()

    for i, rem in enumerate(reminders):

        dt = rem.date + rem.snoozed - now
        relative = f"in {td_format(dt, 'minute')}" if dt > timedelta() else ""
        if rem.snoozed:
            relative += f" (snoozed {td_format(rem.snoozed)})"
        if relative:
            relative += "\n"
        path = ""
        if rem.source != rem.target:
            path = f"\nfrom {rem.source} to {rem.target}"
        tstr = datestr(rem.date + rem.snoozed)
        rpt = f" (every {td_format(rem.repeat)})" if rem.repeat else ""
        cmpl = ":white_check_mark: " if rem.completed else ""

        embed.add_field(name=f"{cmpl} {i + 1}. {rem.task}",
            value=f"{relative}{tstr}{rpt}{path}", inline=False)

        if (i > 0 and (i + 1) % reminders_per_embed == 0) or i + 1 == len(reminders):
            embeds.append(embed)
            embed = discord.Embed()

    return embeds


async def send_reminder_view(ctx, rems: List[Reminder], message="",
    reminders_per_embed=10, embeds_per_message=10):
    embeds = reminders_to_embeds(rems, reminders_per_embed)
    for i in range(0, len(embeds), embeds_per_message):
        em = embeds[i:i+embeds_per_message]
        m = message if i == 0 else ""
        await ctx.send(m, allowed_mentions=DONT_ALERT_USERS, embeds=em)


DISCORD_MENTION_PATTERN = r"<([#@])!?(\d{18})>"


async def fetch_from_mention(client, mention: str):
    match = re.search(DISCORD_MENTION_PATTERN, mention)
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


# return codes
RC_OK = 0
RC_NOT_PROVIDED = 1
RC_OUT_OF_BOUNDS = 2
RC_PARSE_ERROR = 3

def parse_index_from_user_args(arg: str, maxval: int):

    if not arg:
        return None, RC_NOT_PROVIDED
    try:
        index = int(arg) - 1 # users provide [1, N]; CPU uses [0, N - 1]
    except Exception:
        return None, RC_PARSE_ERROR
    if index < 0 or index >= maxval:
        return None, RC_OUT_OF_BOUNDS
    return index, RC_OK


def sanitize_mention(raw: str) -> str:
    match = re.search(DISCORD_MENTION_PATTERN, raw)
    if not match:
        return raw
    prefix = match.group(1)
    uid = match.group(2)
    ret = f"<{prefix}{uid}>"
    return ret


async def get_reminder_index_from_user_interactive(ctx,
    reminders: List[Reminder], arg: str, verb: str, maxval: int):

    index, rc = parse_index_from_user_args(arg, maxval)

    if rc == RC_NOT_PROVIDED:
        if maxval == 1:
            await send_reminder_view(ctx, rems,
                "You only have one reminder, but I still need "
                f"you to explicitly provide the reminder index to {verb} (1).")
        else:
            await send_reminder_view(ctx, rems,
                "Requires the index of the reminder "
                f"you want to {verb} (1 through {maxval}).")
        return index, False
    elif rc == RC_PARSE_ERROR:
        await ctx.send(f"Invalid reminder index: \"{arg}\". Looking for a number between 1 and {maxval}.")
        return index, False
    elif rc == RC_OUT_OF_BOUNDS:
        await ctx.send(f"Provided index {arg} is not within acceptable bounds, 1 through {maxval}.")
        return index, False
    return index, True


class Reminders(commands.Cog):


    def __init__(self, bot, **kwargs):
        self.bot = bot
        self.reminders = get_param("reminders", {}, YAML_PATH)

        deploy_hostname = kwargs.get("deploy_hostname", "")
        hostname = socket.gethostname()

        log.info(f"Deploy hostname: {deploy_hostname}")
        log.info(f"Actual hostname: {hostname}")

        if hostname == deploy_hostname:
            log.info("Starting reminders update loop.")
            self.process_reminders_v2.start()
        else:
            log.warn("In testing environment; disabling reminders spinner!")


    @tasks.loop(seconds=5)
    async def process_reminders_v2(self):
        now = datetime.now()
        triggered_reminders = spin_until(self.reminders, now)
        if not triggered_reminders:
            return
        self.write_reminders_to_disk()
        for event in triggered_reminders:
            log.info(f"Triggered now: {event}")

            source, target = await fetch_reminder_endpoints(self.bot, event)
            embed = remind_event_to_embed(event)
            am = discord.AllowedMentions(users=False)

            if event.source == event.target:
                await target.send(f"Hey, you asked me to "
                    "remind you about this.", embed=embed,
                    allowed_mentions=DONT_ALERT_USERS)
            else:
                await source.send(f"Hey, {event.source}, your reminder to "
                    f"{event.target} just went through.", embed=embed,
                    allowed_mentions=DONT_ALERT_USERS)
                await target.send(f"Hey, {event.target}, a reminder from "
                    f"{event.source} has arrived.", embed=embed,
                    allowed_mentions=DONT_ALERT_USERS)


    def write_reminders_to_disk(self):
        set_param("reminders", self.reminders, YAML_PATH)


    @commands.command()
    async def remind(self, ctx, you_or_someone_else, *task):
        """
        Ask BagelBot to remind you of something.

        Attempts to parse natural human language, so for the most part you can tell BagelBot in the same way you'd ask a person to remind you.

        However, there must be a general structure to the sentence provided, roughly along the lines of

        > bb remind [person] to [do a thing] [at/on/in/by] [some time and date]

        Optionally, the phrase "every N minutes/hours/days" can be included to indicate that you'd like the reminder to fire repeatedly with the specified period.

        You can remind yourself...

        > bb remind me to wash my hair in 45 minutes

        Another person...

        > bb remind @TuftedTitmo to play Raft at 8:30 pm

        Or an entire channel.

        > bb remind #tennisposting to shitpost at 3 am

        Usage:

        > bb remind me to wash the dishes in 4 hours
        > bb remind @ColtsKoala to cross stitch every day at 9 pm
        > bb remind me to do halucenogens every 6 hours at 3:30 pm
        > bb remind me to wash my butt every 4 hours by 11 am
        > bb remind me to eat lunch in 3 hours

        """

        if not task:
            await ctx.send("Requires text input.")
            return
        whoami = sanitize_mention(ctx.message.author.mention)
        text = " ".join([you_or_someone_else, *task])
        now = datetime.now()
        log.debug(f"{ctx.message.author} AKA {whoami}: {text}")
        rem = parse_reminder_text(text, whoami, now)
        if not rem:
            await ctx.send("Sorry, I couldn't understand that. Use " \
                "bb help remind for tips on how to use this command.")
            return

        if rem.date < now:
            await ctx.send("The parsed date for this reminder is in the past. " \
                "Please be more specific about when you'd like me to remind you.",
                embed=reminder_to_embed(rem))
            return

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
        self.write_reminders_to_disk()
        embed = reminder_to_embed(rem)
        you = "you" if rem.source == rem.target else rem.target
        await ctx.send(f"Ok, I'll do my best to remind {you} at "
            "the appropriate time.", embed=embed, allowed_mentions=DONT_ALERT_USERS)


    @commands.command(name="remind-delete", aliases=["rd"])
    async def remind_delete(self, ctx, reminder_to_delete):
        """
        Deletes a reminder from your list.
        To specify which reminder, provide the index of it on your reminders list.

        Use bb remind-list to see your reminders.

        Shorthand: rd

        Providing the words "complete", "completed", "done", or "finished" indicate that you want to delete all completed reminders.

        Usage:

        > bb remind-delete 3
        > bb rd 12
        > bb rd complete

        """
        whoami = sanitize_mention(ctx.message.author.mention)
        uids = get_relevant_tasks(self.reminders, whoami)
        if not uids:
            await ctx.send("You don't have any reminders to delete.")
            return
        rems = [self.reminders[uid] for uid in uids]

        if reminder_to_delete in ["complete", "completed", "done", "finished"]:
            completed_rems = [r for r in rems if r.completed]
            if not completed_rems:
                await ctx.send("None of your reminders are marked complete.")
                return
            await send_reminder_view(ctx, completed_rems, "Deleting these reminders.")
            for r in completed_rems:
                del self.reminders[r.uid]
            self.write_reminders_to_disk()
            return

        N = len(uids)
        index, ok = await get_reminder_index_from_user_interactive(
            ctx, rems, reminder_to_delete, "delete", N)
        if not ok:
            return

        to_delete = rems[index]
        del self.reminders[to_delete.uid]
        self.write_reminders_to_disk()
        embed = reminder_to_embed(to_delete)
        await ctx.send("Deleting this reminder.", embed=embed)


    @commands.command(name="remind-list", aliases=["rls"])
    async def remind_list(self, ctx):
        """
        Shows your list of reminders.
        Will display pending, repeated, and completed reminders.

        Shorthand: rls

        Usage:

        > bb remind-list
        > bb rl

        """
        whoami = sanitize_mention(ctx.message.author.mention)
        uids = get_relevant_tasks(self.reminders, whoami)
        if not uids:
            await ctx.send("You have no reminders.")
            return
        rems = [self.reminders[uid] for uid in uids]
        await send_reminder_view(ctx, rems, "Found these reminders.")


    @commands.command(name="remind-snooze", aliases=["rs"])
    async def remind_snooze(self, ctx, reminder_to_snooze: int):
        """
        Snooze a reminder by 15 minutes.

        If the reminder is single-fire, or if the reminder is repeating, it will delay the next occurrance.

        If the reminder is completed, it will be set as incomplete and trigger 15 minutes from now.

        Shorthand: rs

        Usage:

        > bb remind-snooze 2
        > bb rs 5

        """
        whoami = sanitize_mention(ctx.message.author.mention)
        uids = get_relevant_tasks(self.reminders, whoami)
        if not uids:
            await ctx.send("You don't have any reminders to snooze.")
            return
        rems = [self.reminders[uid] for uid in uids]
        index, ok = await get_reminder_index_from_user_interactive(
            ctx, rems, reminder_to_snooze, "snooze", len(rems))
        if not ok:
            return
        to_snooze = rems[index]

        snooze_delta = timedelta(minutes=15)

        now = datetime.now()
        if to_snooze.completed:
            # mark as incomplete, and put 15 minutes in the future
            to_snooze.date = now + snooze_delta
            to_snooze.snoozed = timedelta()
            to_snooze.completed = False
            msg = "Reviving this reminder, and snoozing " \
                f"until {td_format(snooze_delta)} in the future."
        else:
            to_snooze.snoozed += snooze_delta
            msg = f"Delaying this reminder by {td_format(snooze_delta)}."
        embed = reminder_to_embed(to_snooze)
        await ctx.send(msg, embed=embed)
        add_or_update_reminder(self.reminders, to_snooze)
        self.write_reminders_to_disk()

    @commands.command(name="remind-clear", aliases=["rc"])
    async def remind_clear(self, ctx):
        """
        Deletes all your reminders.

        DANGER: This will delete ALL your reminders.

        Including reminders you've sent to other people, and ones that other people have sent to you.

        Shorthand: rc

        Usage:

        > bb remind-clear
        > bb rc

        """
        whoami = sanitize_mention(ctx.message.author.mention)
        uids = get_relevant_tasks(self.reminders, whoami)
        if not uids:
            await ctx.send("You don't have any reminders to delete.")
            return
        to_delete = [self.reminders[uid] for uid in uids]
        for rem in to_delete:
            del self.reminders[rem.uid]
        self.write_reminders_to_disk()
        await send_reminder_view(ctx, to_delete, ":boom: Bam! :boom: Deleted these reminders.")


if __name__ == "__main__":
    main()








