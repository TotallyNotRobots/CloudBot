from datetime import datetime, date, timedelta

import pytest


class Call:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def call(self, func):
        return func(*self.args, **self.kwargs)


@pytest.mark.parametrize(
    "call,result",
    [
        # basic
        (Call(120000), "1 day, 9 hours and 20 minutes"),
        (Call(120000, simple=True), "1d 9h 20m"),

        # count
        (Call(1200003, count=4), "13 days, 21 hours, 20 minutes and 3 seconds"),
        (Call(1200000, count=4), "13 days, 21 hours and 20 minutes"),
        (Call(1200000, count=2), "13 days and 21 hours"),
    ]
)
def test_format_time(call, result):
    from cloudbot.util.timeformat import format_time
    assert call.call(format_time) == result


def test_timesince():
    from cloudbot.util.timeformat import time_since
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
    # day conversion
    assert time_since(date(2010, 5, 14), now) == "1 day and 1 hour"
    assert time_since(date(2010, 5, 14), date(2010, 5, 17)) == "3 days"

    assert time_since(datetime.now() - timedelta(days=1, hours=2)) == "1 day and 2 hours"


def test_timeuntil():
    from cloudbot.util.timeformat import time_until
    now = datetime(2010, 4, 12, 12, 30, 0)
    future = datetime(2010, 5, 15, 1, 50, 0)
    # basic
    assert time_until(future, now) == "1 month and 2 days"
    # count
    assert time_until(future, now, count=3) == "1 month, 2 days and 13 hours"

    assert time_until(datetime.now() + timedelta(days=2, hours=5)) == "2 days and 5 hours"
