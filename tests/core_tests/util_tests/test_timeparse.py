def test_time_parse():
    from cloudbot.util.timeparse import time_parse

    assert time_parse("1:24") == 84
    assert time_parse(":22") == 22
    assert time_parse("1 minute, 24 secs") == 84
    assert time_parse("1m24s") == 84
    assert time_parse("1.2 minutes") == 72
    assert time_parse("1.2 seconds") == 1.2
    assert time_parse("- 1 minute") == -60
    assert time_parse("+ 1 minute") == 60
    assert time_parse("1:30") == 90
    assert time_parse("1:30", granularity="minutes") == 5400
