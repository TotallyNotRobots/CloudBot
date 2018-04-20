import pytest


@pytest.mark.parametrize("args,kwargs,result", [
    (['1:24'], {}, 84),
    ([':22'], {}, 22),
    (['1 minute, 24 secs'], {}, 84),
    (['1m24s'], {}, 84),
    (['1.2 minutes'], {}, 72),
    (['1.2 seconds'], {}, 1.2),
    (['- 1 minute'], {}, -60),
    (['+ 1 minute'], {}, 60),
    (['1:30'], {}, 90),
    (['1:30'], {'granularity': 'minutes'}, 5400),
])
def test_time_parse(args, kwargs, result):
    from cloudbot.util.timeparse import time_parse
    assert time_parse(*args, **kwargs) == result
