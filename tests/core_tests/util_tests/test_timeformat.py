from datetime import datetime, timedelta

from cloudbot.util import timeformat
from cloudbot.util.timeformat import format_time, time_since, time_until


def test_time_split():
    parsed = timeformat.TimeUnits.split_time(0)
    assert parsed.parts == [
        (0, timeformat.TimeUnits.YEAR),
        (0, timeformat.TimeUnits.MONTH),
        (0, timeformat.TimeUnits.DAY),
        (0, timeformat.TimeUnits.HOUR),
        (0, timeformat.TimeUnits.MINUTE),
        (0, timeformat.TimeUnits.SECOND),
    ]

    parsed = timeformat.TimeUnits.split_time(1)
    assert parsed.parts == [
        (0, timeformat.TimeUnits.YEAR),
        (0, timeformat.TimeUnits.MONTH),
        (0, timeformat.TimeUnits.DAY),
        (0, timeformat.TimeUnits.HOUR),
        (0, timeformat.TimeUnits.MINUTE),
        (1, timeformat.TimeUnits.SECOND),
    ]

    parsed = timeformat.TimeUnits.split_time(2)
    assert parsed.parts == [
        (0, timeformat.TimeUnits.YEAR),
        (0, timeformat.TimeUnits.MONTH),
        (0, timeformat.TimeUnits.DAY),
        (0, timeformat.TimeUnits.HOUR),
        (0, timeformat.TimeUnits.MINUTE),
        (2, timeformat.TimeUnits.SECOND),
    ]


def test_format_time():
    # basic
    assert format_time(120000) == "1 day, 9 hours and 20 minutes"
    assert format_time(120000, simple=True) == "1d 9h 20m"
    # count
    assert (
        format_time(1200003, count=4)
        == "13 days, 21 hours, 20 minutes and 3 seconds"
    )
    assert format_time(1200000, count=4) == "13 days, 21 hours and 20 minutes"
    assert format_time(1200000, count=2) == "13 days and 21 hours"

    assert format_time(0) == "0 seconds"
    assert format_time(1) == "1 second"
    assert format_time(2) == "2 seconds"


def test_timesince():
    then = datetime(2010, 4, 12, 12, 30, 0)
    then_timestamp = 1271075400.0
    then_future = datetime(2012, 4, 12, 12, 30, 0)
    now = datetime(2010, 5, 15, 1, 50, 0)
    now_timestamp = 1273888200.0
    # timestamp
    assert time_since(then_timestamp, now_timestamp) == "1 month and 2 days"
    # basic
    assert time_since(then, now) == "1 month and 2 days"
    # count
    assert time_since(then, now, count=3) == "1 month, 2 days and 13 hours"
    # future
    assert time_since(then_future, now) == "0 minutes"

    assert time_since(then.date(), now.date()) == "1 month and 3 days"

    assert time_since(datetime.now() - timedelta(hours=2)) == "2 hours"

    assert time_since(now - timedelta(seconds=0), now) == "0 minutes"
    assert time_since(now - timedelta(seconds=1), now) == "1 second"
    assert time_since(now - timedelta(seconds=2), now) == "2 seconds"


def test_timeuntil():
    now = datetime(2010, 4, 12, 12, 30, 0)
    future = datetime(2010, 5, 15, 1, 50, 0)
    # basic
    assert time_until(future, now) == "1 month and 2 days"
    # count
    assert time_until(future, now, count=3) == "1 month, 2 days and 13 hours"

    assert time_until(datetime.now() + timedelta(hours=2)) == "2 hours"
