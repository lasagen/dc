#!/usr/bin/env python3

from bs4 import BeautifulSoup
from collections import namedtuple
from datetime import datetime
import re
import requests
import sys


root = "https://www.dancecomplex.org/classes-workshops/"

age_limit_regex = re.compile(r"\(Age.*\)")
start_dt_format = '%B %d @ %I:%M %p'
end_dt_format = '%I:%M %p'
# dc_tz = pytz.timezone('US/Eastern')

DanceClass = namedtuple('DanceClass',
                        ['title', 'start_dt', 'end_t', 'studio'])


def request_wrapped(path):
    try:
        r = requests.get(path)
        if r.ok:
            print(f"Got a response from {path}\n")
        else:
            raise(ValueError(f"Status code {r.status_code}"))
    except Exception as e:
        print(f"Request to {path} failed :( \nDetails: {e}")
        sys.exit(1)
    return r


if __name__ == '__main__':
    r = request_wrapped(root)
    soup = BeautifulSoup(r.text, "html.parser")

    raw_titles = soup.find_all("a", {"class": "tribe-events-calendar-day__event-title-link tribe-common-anchor-thin"})
    raw_date_start = soup.find_all("span", {"class": "tribe-event-date-start"})
    raw_time_end = soup.find_all("span", {"class": "tribe-event-time"})
    raw_studios = soup.find_all("span", {"class": "tribe-events-calendar-day__event-venue-title tribe-common-b2--bold"})

    stripped_strings = map(
        lambda l: [x.string.strip() for x in l],
        [raw_titles, raw_date_start, raw_time_end, raw_studios]        
    )

    table = zip(*stripped_strings)
    
    classes = [DanceClass(t,
                          datetime.strptime(ds, start_dt_format),
                          datetime.strptime(de, end_dt_format),
                          s)
               for t, ds, de, s in table]
    
    adult_classes = filter(
        lambda c: not age_limit_regex.search(c.title), classes)
    
    for c in adult_classes:
        print(c.title)
        duration = (c.end_t - c.start_dt).seconds / 3600
        print(f"{c.start_dt.strftime('%B %d | %I:%M %p')} - \
{c.end_t.strftime('%I:%M %p')} ({duration} hours)")
        state = ""
        now = datetime.now()
        end_dt = c.end_t.replace(
            year=now.year, month=c.start_dt.month, day=c.start_dt.day)
        if now > end_dt:
            state = "Ended"
        elif now < c.start_dt:
            state = "Upcoming"
        else:
            state = "In Progress"
        print(f"{state} | {c.studio}")
        print()