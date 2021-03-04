"""
timeformat.py

Contains functions to format time periods. Based on code from the Django project and CloudBot contributors.

The licensing for this module isn't solid, because I started working on this module before I had a proper
system for tracking code licences. If your code is in this file and you have any queries, contact me by
email at <lukeroge@gmail.com>!

Maintainer:
    - Luke Rogers <https://github.com/lukeroge>

License:
    BSD license

    Copyright (c) Django Software Foundation and individual contributors.
    All rights reserved.

    Redistribution and use in source and binary forms, with or without modification,
    are permitted provided that the following conditions are met:

        1. Redistributions of source code must retain the above copyright notice,
           this list of conditions and the following disclaimer.

        2. Redistributions in binary form must reproduce the above copyright
           notice, this list of conditions and the following disclaimer in the
           documentation and/or other materials provided with the distribution.

        3. Neither the name of Django nor the names of its contributors may be used
           to endorse or promote products derived from this software without
           specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
    ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
    ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
    (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
    ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import datetime

from cloudbot.util import formatting
from cloudbot.util.formatting import pluralize_select


def time_since(d, now=None, count=2, accuracy=6, simple=False):
    """
    Takes two datetime objects and returns the time between d and now
    as a nicely formatted string, e.g. "10 minutes". If d occurs after now,
    then "0 minutes" is returned.
    This function has a number of optional arguments that can be combined:

    SIMPLE: displays the time in a simple format
    >>> NOW = datetime.datetime.now()
    >>> SECONDS = NOW - datetime.timedelta(hours=1, minutes=2, seconds=34)
    >>> timesince(SECONDS, now=NOW)
    '1 hour and 2 minutes'
    >>> timesince(SECONDS, simple=True, now=NOW)
    '1h 2m'

    COUNT: how many periods should be shown (default 3)
    >>> DIFF = datetime.timedelta(seconds=4663419154)
    >>> SECONDS = NOW - DIFF
    >>> timesince(SECONDS, now=NOW)
    '147 years and 10 months'
    >>> timesince(SECONDS, count=6, now=NOW)
    '147 years, 10 months, 19 days, 18 hours, 12 minutes and 34 seconds'
    """

    # Convert int or float (unix epoch) to datetime.datetime for comparison
    if isinstance(d, (int, float)):
        d = datetime.datetime.fromtimestamp(d)

    if isinstance(now, (int, float)):
        now = datetime.datetime.fromtimestamp(now)

    # Convert datetime.date to datetime.datetime for comparison.
    if not isinstance(d, datetime.datetime):
        d = datetime.datetime(d.year, d.month, d.day)
    if now and not isinstance(now, datetime.datetime):
        now = datetime.datetime(now.year, now.month, now.day)

    if not now:
        now = datetime.datetime.now()

    # ignore microsecond part of 'd' since we removed it from 'now'
    delta = now - (d - datetime.timedelta(0, 0, d.microsecond))
    since = delta.days * 24 * 60 * 60 + delta.seconds

    if since <= 0:
        # d is in the future compared to now, stop processing.
        return "0 " + "minutes"

    # pass the number in seconds on to format_time to make the output string
    return format_time(since, count, accuracy, simple)


# compatibility
timesince = time_since


def time_until(d, now=None, count=2, accuracy=6, simple=False):
    """
    Like timesince, but returns a string measuring the time until
    the given time.
    """
    if not now:
        now = datetime.datetime.now()
    return time_since(now, d, count, accuracy, simple)


# compatibility
timeuntil = time_until


class TimeUnit:
    """
    >>> t = TimeUnit(3600, 'h', 'hour', 'hours')
    >>> t * 24
    86400
    >>> t * 2
    7200
    """

    def __init__(self, seconds, short_name, long_name, long_name_plural):
        self.seconds = seconds
        self.short_name = short_name
        self.long_name = long_name
        self.long_name_plural = long_name_plural

    def __repr__(self):
        fields = ("seconds", "short_name", "long_name", "long_name_plural")
        return "TimeUnit({})".format(
            ", ".join(f"{k}={getattr(self, k)!r}" for k in fields)
        )

    def __mul__(self, other):
        return self.seconds * other

    def __rmul__(self, other):
        return other * self.seconds

    def format(self, count, simple=True):
        if simple:
            return "{:,}{}".format(count, self.short_name)

        return pluralize_select(count, self.long_name, self.long_name_plural)


class TimeInterval:
    def __init__(self, parts):
        self.parts = parts

    def format(self, simple=True, skip_empty=True, count=3):
        i = 0
        out = []
        for num, unit in self.parts:
            if i >= count:
                break

            if num <= 0 and skip_empty:
                continue

            i += 1
            out.append(unit.format(num, simple=simple))

        if not out:
            out.append(TimeUnits.SECOND.format(0, simple=simple))

        if simple:
            return " ".join(out)

        return formatting.get_text_list(out, "and")


class TimeUnits:
    SECOND = TimeUnit(1, "s", "second", "seconds")
    MINUTE = TimeUnit(60 * SECOND, "m", "minute", "minutes")
    HOUR = TimeUnit(60 * MINUTE, "h", "hour", "hours")
    DAY = TimeUnit(24 * HOUR, "d", "day", "days")
    MONTH = TimeUnit(30 * DAY, "M", "month", "months")
    YEAR = TimeUnit(365 * DAY, "y", "year", "years")
    DECADE = TimeUnit(10 * YEAR, "D", "decade", "decades")
    CENTURY = TimeUnit(10 * DECADE, "c", "century", "centuries")

    units = (CENTURY, DECADE, YEAR, MONTH, DAY, HOUR, MINUTE, SECOND)

    @classmethod
    def split_time(cls, seconds, accuracy=6):
        out = []
        for unit in cls.units[-accuracy:]:
            if seconds > unit.seconds:
                p_val, seconds = divmod(seconds, unit.seconds)
            else:
                p_val = 0

            out.append((p_val, unit))

        out[-1] = (out[-1][0] + seconds, out[-1][1])

        return TimeInterval(out)


def format_time(seconds, count=3, accuracy=6, simple=False):
    """
    Takes a length of time in seconds and returns a string describing that length of time.
    This function has a number of optional arguments that can be combined:

    SIMPLE: displays the time in a simple format
    >>> SECONDS = int(datetime.timedelta(hours=1, minutes=2, seconds=34).total_seconds())
    >>> format_time(SECONDS)
    '1 hour, 2 minutes and 34 seconds'
    >>> format_time(SECONDS, simple=True)
    '1h 2m 34s'

    COUNT: how many periods should be shown (default 3)
    >>> SECONDS = 4663419154
    >>> format_time(SECONDS)
    '147 years, 10 months and 19 days'
    >>> format_time(SECONDS, count=6)
    '147 years, 10 months, 19 days, 18 hours, 12 minutes and 34 seconds'
    >>> format_time(3600)
    '60 minutes'
    """

    parsed = TimeUnits.split_time(seconds, accuracy=accuracy)

    return parsed.format(simple=simple, count=count)
