from cloudbot.util import timeparse


def test_time_parse():
    assert timeparse.time_parse("1:24") == 84
    assert timeparse.time_parse(":22") == 22
    assert timeparse.time_parse("1 minute, 24 secs") == 84
    assert timeparse.time_parse("1m24s") == 84
    assert timeparse.time_parse("1.2 minutes") == 72
    assert timeparse.time_parse("1.2 seconds") == 1.2
    assert timeparse.time_parse("- 1 minute") == -60
    assert timeparse.time_parse("+ 1 minute") == 60
    assert timeparse.time_parse("1:30") == 90
    assert timeparse.time_parse("1:30", granularity="minutes") == 5400
    assert timeparse.time_parse("foo") is None
