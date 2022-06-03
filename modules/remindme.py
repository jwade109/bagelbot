#! /usr/bin/env python3

import sys
import os
from dataclasses import dataclass
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


def datestr(date: datetime) -> str:
    return date.strftime('%I:%M %p on %B %d, %Y')


def reminder_msg(rem: datetime) -> str:
    dstr = datestr(rem.date)
    return f"Hey {rem.target}, {rem.source} asked me to remind you to " \
        f"\"{rem.task}\" at {dstr}, which is right about now."


# returns the closest future date for which this reminder
# is relevant; for completed reminders, returns None;
# for reminders which are not complete, returns the reminder
# date or the current time, whichever is later
def get_next_reminder_time(rem) -> datetime:
    if rem.completed:
        return None
    now = datetime.now()
    return max(now, rem.date)


def parse_reminder_text(text, source):
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


def do_snooze(text, reminders):
    sr = parse_snooze_request(text)
    if not sr:
        return
    rem = find_task(sr.task, reminders)
    if not rem:
        return
    print_reminders([rem])
    if sr.delta:
        print(f"Delay task {rem.task} by {sr.delta}.")
        delta = sr.delta
    else:
        print(f"Delay task {rem.task} until {sr.until}.")
        delta = sr.until - rem.date
    print(f"Delay by {delta}.")
    rem.snooze = delta



def print_reminders(remlist):
    for rem in remlist:
        nrt = datestr(get_next_reminder_time(rem))
        dailystr = " (daily)" if rem.daily else ""
        print(f"- {rem.task}{dailystr}, at {datestr(rem.date)} ({nrt})")


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


def main():

    REMINDERS = [parse_reminder_text(x, "module") for x in [
        "me to do the dishes by tomorrow",
        "me to do my homework in 4 days",
        "me view the quadrantids meteor shower on January 2, 2024, 1 am",
        "me eat a krabby patty at 3 am",
        "me to brush my teeth every day at noon",
        "me daily to scream at the moon in 1 hour",
        "me to do the do at 12 pm"
    ]]

    while True:

        print(f" bb remind > ", end="");
        sys.stdout.flush();
        text = input()
        if not text:
            continue
        args = text.split(" ")

        if text == "tasks":
            print_reminders(REMINDERS)
            continue
        if args[0] == "snooze":
            do_snooze(text, REMINDERS)
            continue

        rem = parse_reminder_text(text, "Sue")
        if rem:
            print(rem)
            print(reminder_msg(rem))
            REMINDERS.append(rem)


if __name__ == "__main__":
    main()

