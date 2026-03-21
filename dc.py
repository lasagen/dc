#!/usr/bin/env python3

from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import msgspec
import os
import re
import requests


root = 'https://www.dancecomplex.org/classes-workshops/'

age_limit_regex = re.compile(r'\(Age.*\)')
start_dt_format = '%B %d @ %I:%M %p'
end_dt_format = '%I:%M %p'
dc_tz = ZoneInfo('US/Eastern')

CACHE_FILENAME = './cache.jsonl'
TTL = 3600


class DanceClass(msgspec.Struct):
    title: str
    start_dt: datetime
    end_dt: datetime
    studio: str
    link: str


def request_wrapped(path):
    try:
        response = requests.get(path)
        if response.ok:
            print(f'Got a response from {path}\n')
        else:
            raise(ValueError(f'Status code {response.status_code}'))
    except Exception as err:
        print(f'Request to {path} failed :( \nDetails: {err}')
        exit(1)
    return response


def display(adult_classes):
    now = datetime.now().astimezone()
    for c in adult_classes:
        print(c.title)
        duration = (c.end_dt - c.start_dt).seconds / 3600
        print(f"{c.start_dt.strftime('%B %d | %I:%M %p')} - \
{c.end_dt.strftime('%I:%M %p')} ({duration} hours)")
        state = ''
        if now > c.end_dt:
            state = 'Ended'
        elif now < c.start_dt:
            state = 'Upcoming'
        else:
            state = 'In Progress'
        print(f'{state} | {c.studio}')
        print()


if __name__ == '__main__':
    stat = os.stat(CACHE_FILENAME)
    mtime_epoch = stat.st_mtime
    mtime = datetime.fromtimestamp(mtime_epoch)
    now = datetime.now()
    elapsed = (now - mtime).total_seconds()
    
    if elapsed < TTL:
        print(f'Loading dance class info from {CACHE_FILENAME}\n')
        with open(CACHE_FILENAME, 'rb') as f:
            classes_bytes = f.read().splitlines()
        adult_classes = [msgspec.json.decode(obj, type=DanceClass)
                        for obj in classes_bytes]
    else:
        response = request_wrapped(root)
        soup = BeautifulSoup(response.text, 'html.parser')

        raw_titles = soup.find_all('a', {'class': 'tribe-events-calendar-day__event-title-link tribe-common-anchor-thin'}, href=True)
        raw_date_start = soup.find_all('span', {'class': 'tribe-event-date-start'})
        raw_time_end = soup.find_all('span', {'class': 'tribe-event-time'})
        raw_studios = soup.find_all('span', {'class': 'tribe-events-calendar-day__event-venue-title tribe-common-b2--bold'})

        stripped_strings = list(map(
            lambda lst: [x.string.strip() for x in lst],
            [raw_titles, raw_date_start, raw_time_end, raw_studios]        
        ))
        stripped_strings.append([title['href'] for title in raw_titles])

        table = zip(*stripped_strings)
        now = datetime.now().astimezone()
        
        classes = [DanceClass(title,
                            datetime.strptime(date_start, start_dt_format)
                            .replace(year=now.year, tzinfo=dc_tz),
                            datetime.strptime(time_end, end_dt_format)
                            .replace(year=now.year, tzinfo=dc_tz),
                            studio,
                            link)
                for title, date_start, time_end, studio, link in table]
        for c in classes:
            c.end_dt = c.end_dt.replace(month=c.start_dt.month, day=c.start_dt.day)
        
        # filter by title to reduce number of requests
        maybe_adult_classes = [c for c in classes
                            if not age_limit_regex.search(c.title)]
        
        # check filtered pages for 'Classes for Adults' category
        # not worrying about page location for now
        adult_classes = [c for c in maybe_adult_classes
                        if 'Classes for Adults' in request_wrapped(c.link).text]
        
        print(f'Storing dance class info in {CACHE_FILENAME}')
        with open(CACHE_FILENAME, 'wb') as f:
            for c in adult_classes:
                f.write(msgspec.json.encode(c))
                f.write(b'\n')
    
    display(adult_classes)
