#!/usr/bin/env python3

from bs4 import BeautifulSoup
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo
import re
import requests
import sys


root = "https://www.dancecomplex.org/classes-workshops/"

age_limit_regex = re.compile(r"\(Age.*\)")
start_dt_format = '%B %d @ %I:%M %p'
end_dt_format = '%I:%M %p'
dc_tz = ZoneInfo('US/Eastern')

@dataclass
class DanceClass:
    title: str
    start_dt: datetime
    end_dt: datetime
    studio: str


def request_wrapped(path):
    try:
        response = requests.get(path)
        if response.ok:
            print(f"Got a response from {path}\n")
        else:
            raise(ValueError(f"Status code {response.status_code}"))
    except Exception as err:
        print(f"Request to {path} failed :( \nDetails: {err}")
        sys.exit(1)
    return response


if __name__ == '__main__':
    response = request_wrapped(root)
    soup = BeautifulSoup(response.text, "html.parser")

    raw_titles = soup.find_all("a", {"class": "tribe-events-calendar-day__event-title-link tribe-common-anchor-thin"})
    raw_date_start = soup.find_all("span", {"class": "tribe-event-date-start"})
    raw_time_end = soup.find_all("span", {"class": "tribe-event-time"})
    raw_studios = soup.find_all("span", {"class": "tribe-events-calendar-day__event-venue-title tribe-common-b2--bold"})

    stripped_strings = map(
        lambda lst: [x.string.strip() for x in lst],
        [raw_titles, raw_date_start, raw_time_end, raw_studios]        
    )

    table = zip(*stripped_strings)
    now = datetime.now().replace(tzinfo=dc_tz)
    
    classes = [DanceClass(title,
                          datetime.strptime(date_start, start_dt_format)
                          .replace(year=now.year, tzinfo=dc_tz),
                          datetime.strptime(time_end, end_dt_format)
                          .replace(year=now.year, tzinfo=dc_tz),
                          studio)
               for title, date_start, time_end, studio in table]
    for c in classes:
        c.end_dt = c.end_dt.replace(month=c.start_dt.month, day=c.start_dt.day)
    
    adult_classes = filter(
        lambda c: not age_limit_regex.search(c.title), classes)
    
    for c in adult_classes:
        print(c.title)
        duration = (c.end_dt - c.start_dt).seconds / 3600
        print(f"{c.start_dt.strftime('%B %d | %I:%M %p')} - \
{c.end_dt.strftime('%I:%M %p')} ({duration} hours)")
        state = ""
        if now > c.end_dt:
            state = "Ended"
        elif now < c.start_dt:
            state = "Upcoming"
        else:
            state = "In Progress"
        print(f"{state} | {c.studio}")
        print()