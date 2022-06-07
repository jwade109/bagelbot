#! /usr/bin/env python3

import sys
import os
from dataclasses import dataclass
from typing import List
import re
from datetime import datetime, timedelta
from dateparser import parse as dateparse
import random
from fuzzywuzzy import fuzz
import warnings
from pytimeparse.timeparse import timeparse


# ignore dateparser warnings
warnings.filterwarnings("ignore",
    message="The localize method is no longer necessary, " \
    "as this time zone supports the fold attribute")


@dataclass()
class Reminder:
    target: str = ""
    source: str = ""
    date: datetime = None
    task: str = ""
    daily: bool = False
    completed: bool = False
    snoozed: timedelta = timedelta()


def datestr(date: datetime) -> str:
    return date.strftime('%I:%M %p on %B %d, %Y')


def reminder_msg(rem: Reminder) -> str:
    dstr = datestr(rem.date)
    return f"Hey {rem.target}, {rem.source} asked me to remind you to " \
        f"\"{rem.task}\" at {dstr}, which is right about now."


# returns the closest future date for which this reminder
# is relevant; for completed reminders, returns None;
# for reminders which are not complete, returns the reminder
# date or the current time, whichever is later
def get_next_reminder_time(rem: Reminder, now: datetime) -> datetime:
    if rem.completed:
        return None
    return max(now, rem.date + rem.snoozed)


def parse_reminder_text(text: str, source: str):
    ret = Reminder()
    daily_pattern = r"(\s(on the daily|daily|every day))"
    base_pattern = r"(.+?)\s(to\s)?(.*)\s((at|on|in|by)\b.+\b)"
    daily_matches = re.search(daily_pattern, text)
    if daily_matches:
        ret.daily = True
        text = re.sub(daily_pattern, "", text, 1)
    matches = re.search(base_pattern, text)
    if not matches:
        print("Doesn't match regex.")
        return None
    target = matches.group(1)
    thing_to_do = matches.group(3)
    datestr = matches.group(4)
    date = dateparse(datestr)
    if not date:
        print(f"Unparseable date: {datestr}")
        return None
    if date < datetime.now():
        print("Date is in the past.")
        return None
    ret.target = target
    ret.source = source
    ret.date = date
    ret.task = thing_to_do
    return ret


@dataclass()
class SnoozeRequest:
    task: str = ""
    delta: timedelta = None
    until: datetime = None


def parse_snooze_request(text):
    pattern = r"snooze\s(.*)\s(until|by|for)(\b.+\b)"
    matches = re.search(pattern, text)
    if not matches:
        print("Snooze request doesn't match regex.")
        return None
    sr = SnoozeRequest()
    sr.task = matches.group(1)
    sr.delta = timeparse(matches.group(3))
    if sr.delta is None:
        sr.until = dateparse(matches.group(3))
        if not sr.until:
            print("Bad timedelta string.")
            return None
    else:
        sr.delta = timedelta(seconds=sr.delta)
    return sr


def do_snooze(text, reminders, now):
    sr = parse_snooze_request(text)
    if not sr:
        return
    rems = find_task(sr.task, reminders)
    if len(rems) == 0:
        print(f"No reminders found with search \"{sr.task}\".")
        return
    if len(rems) > 1 and rems[0][0] < 90:
        print(f"Ambigous search \"{sr.task}\"; got these reminders:")
        for r in rems:
            print(f" - {r[1].task:40s}{r[0]}%")
        return
    rem = rems[0][1]
    index = reminders.index(rem) # inefficient
    if not rem:
        return
    print_reminders([rem], now)
    if sr.delta is not None:
        print(f"Delay task {rem.task} by {sr.delta}.")
        delta = sr.delta
        rem.snoozed += delta
    elif sr.until is not None:
        print(f"Delay task {rem.task} until {sr.until}.")
        delta = sr.until - rem.date
        rem.snoozed += delta
    else:
        print(f"Bad snooze request: {sr}")
        return
    reminders[index] = rem


def print_reminders(remlist, now, show_completed=False):
    for rem in remlist:
        if (not show_completed) and rem.completed:
            continue
        time = get_next_reminder_time(rem, now)
        nrt = "completed" if time is None else datestr(time)
        dailystr = " D" if rem.daily else ""
        snoozestr = ""
        if rem.snoozed:
            snoozestr = f" (snoozed {rem.snoozed})"
        # print(rem)
        route = f"- from {rem.source} to {rem.target}:"
        print(f"{route:30s}{nrt:30s}{dailystr:5s}{rem.task:40s}{snoozestr}")


def find_task(search, reminders):
    results = []
    for rem in reminders:
        r = fuzz.ratio(search, rem.task)
        results.append((r, rem))
    results.sort(key=lambda r: -r[0]) # sort so the best match is first
    return results


def is_relevant_to(rem: Reminder, agent_name: str) -> bool:
    if not agent_name:
        return True
    return rem.source == agent_name or rem.target == agent_name


# if the reminder is single-fire, marks complete;
# otherwise, advances the timestamp to the next future date
def mark_complete_or_advance(rem: Reminder, now: datetime):
    if not rem.daily:
        rem.completed = True
        return
    while rem.date <= now:
        rem.date += timedelta(days=1)
        rem.snooze = timedelta()


def spin_once(start: datetime, stop: datetime, reminders: List[Reminder]) -> List[Reminder]:
    # print(f"Spinning: {datestr(start)} to {datestr(stop)}.")
    results = []
    for rem in reminders:
        if rem.completed:
            continue
        time = get_next_reminder_time(rem, start)
        if time >= start and time <= stop:
            mark_complete_or_advance(rem, stop)
            results.append(rem)
    return results


def main():

    prt = parse_reminder_text

    REMINDERS = [
        prt("John to do the dishes every day at 7:30 pm", "Sally"),
        prt("me to do the dishes by tomorrow", "me"),
        prt("Paul to do my homework in 4 days", "me"),
        prt("John view the quadrantids meteor shower on January 2, 2024, 1 am", "John"),
        prt("Paul eat a krabby patty at 3 am tomorrow", "Sally"),
        prt("me to brush my teeth every 8 hours in 3 hours", "John"),
        prt("me daily to scream at the moon in 1 hour", "me"),
        prt("Sally to do the do at 12 pm tomorrow", "me"),
        prt("Sally to get gud in 3 minutes", "Sally")
    ]

    NOW = datetime.now()
    SPIN_RESOLUTION = timedelta(hours=1)

    # REMINDERS[1].snoozed = timedelta(hours=1, minutes=20)

    while True:

        print(f"\n ---------- {datestr(NOW)} / bb remind > ", end="");
        sys.stdout.flush();
        text = input()
        if not text:
            text = "spin"
        args = text.split(" ")

        if args[0] == "c":
            os.system("cls")
            continue
        if args[0] == "tasks":
            user = ""
            if len(args) > 1:
                user = args[1]
            rem = [r for r in REMINDERS if is_relevant_to(r, user)]
            print_reminders(rem, NOW, False)
            continue
        if args[0] == "snooze":
            do_snooze(text, REMINDERS, NOW)
            continue
        if args[0] == "spin":
            start = NOW
            NOW += SPIN_RESOLUTION
            end = NOW
            rems = spin_once(start, end, REMINDERS)
            print_reminders(rems, NOW, True)
            continue

        rem = parse_reminder_text(text, "Sue")
        if rem:
            print(rem)
            print(reminder_msg(rem))
            REMINDERS.append(rem)


if __name__ == "__main__":
    main()

