from plugins import wyr


def test_wyr():
    assert wyr.wyr() == "rrrather.com has been retired"
