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


# Ignore dateparser warnings regarding pytz
warnings.filterwarnings(
    "ignore",
    message="The localize method is no longer necessary, as this time zone supports the fold attribute",
)


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
    rem = find_task(sr.task, reminders)
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
        dailystr = " (daily)" if rem.daily else ""
        snoozestr = ""
        if rem.snoozed:
            snoozestr = f" (snoozed {rem.snoozed})"
        # print(rem)
        print(f"- from {rem.source} to {rem.target}:")
        print(f"  {rem.task}{dailystr}, at {datestr(rem.date)}{snoozestr} ({nrt})")


def find_task(search, reminders):
    results = []
    for rem in reminders:
        r = fuzz.ratio(search, rem.task)
        if r > 70:
            results.append((r, rem))
    results.sort()
    if not results:
        return None
    return results[-1][1]


# if the reminder is single-fire, marks complete;
# otherwise, advances the timestamp to the next future date
def mark_complete_or_advance(rem: Reminder, now: datetime):
    if not rem.daily:
        rem.completed = True
        return
    while rem.date <= now:
        rem.date += timedelta(days=1)


def spin_once(start: datetime, stop: datetime, reminders: List[Reminder]) -> List[Reminder]:
    # print(f"Spinning: {datestr(start)} to {datestr(stop)}.")
    results = []
    for rem in reminders:
        if rem.completed:
            continue
        time = get_next_reminder_time(rem)
        if time >= start and time <= stop:
            mark_complete_or_advance(rem, stop)
            results.append(rem)
    return results


def main():

    REMINDERS = [parse_reminder_text(x, "module") for x in [
        "me to do the dishes every day at 7:30 pm"
        # "me to do the dishes by tomorrow",
        # "me to do my homework in 4 days",
        # "me view the quadrantids meteor shower on January 2, 2024, 1 am",
        # "me eat a krabby patty at 3 am tomorrow",
        # "me to brush my teeth every day in 3 hours",
        # "me daily to scream at the moon in 1 hour",
        # "me to do the do at 12 pm tomorrow",
        # "<@235584665564610561> to get gud in 3 minutes"
    ]]

    NOW = datetime.now()
    SPIN_RESOLUTION = timedelta(hours=1)

    # REMINDERS[1].snoozed = timedelta(hours=1, minutes=20)

    while True:

        print(f"{datestr(NOW)} / bb remind > ", end="");
        sys.stdout.flush();
        text = input()
        if not text:
            text = "spin"
        args = text.split(" ")

        if text == "tasks":
            print_reminders(REMINDERS, NOW)
            continue
        if args[0] == "snooze":
            do_snooze(text, REMINDERS)
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

