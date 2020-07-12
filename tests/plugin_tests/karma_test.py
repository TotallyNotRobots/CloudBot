from unittest.mock import MagicMock, call

from plugins import karma


def test_remove_non_chan(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)

    data = [
        {"name": "foo", "chan": "thing", "thing": "bar", "score": 5},
        {"name": "foo", "chan": "thing1", "thing": "bar1", "score": 5},
        {"name": "foo2", "chan": "#foo", "thing": "baz", "score": 5},
    ]
    for row in data:
        mock_db.add_row(karma.karma_table, **row)

    karma.remove_non_channel_points(mock_db.session())

    assert mock_db.get_data(karma.karma_table) == [("foo2", "#foo", "baz", 5)]


def test_addpoint(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)

    assert mock_db.get_data(karma.karma_table) == []

    karma.addpoint("foo", "bar", "#baz", mock_db.session())

    assert mock_db.get_data(karma.karma_table) == [("bar", "#baz", "foo", 1)]

    karma.addpoint("foo", "bar", "#baz", mock_db.session())

    assert mock_db.get_data(karma.karma_table) == [("bar", "#baz", "foo", 2)]


def test_addpoint_non_channel(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)

    assert mock_db.get_data(karma.karma_table) == []

    karma.addpoint("foo", "bar", "bar", mock_db.session())

    assert mock_db.get_data(karma.karma_table) == []


def test_re_addpt(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    match = karma.karmaplus_re.search("some thing++")

    mock = MagicMock()
    karma.re_addpt(match, "foo", "bar", mock_db.session(), mock)

    assert mock.mock_calls == []

    assert mock_db.get_data(karma.karma_table) == [
        ("foo", "bar", "some thing", 1)
    ]


def test_re_addpt_pluspts(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    data = [{"name": "foo", "chan": "#bar", "thing": "baz", "score": 5}]
    for row in data:
        mock_db.add_row(karma.karma_table, **row)

    match = karma.karmaplus_re.search("++")

    mock = MagicMock()
    karma.re_addpt(match, "foo", "#bar", mock_db.session(), mock)

    assert mock.mock_calls == [call("baz has 5 points ")]


def test_re_rmpt(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    match = karma.karmaminus_re.search("some thing--")

    mock = MagicMock()
    karma.re_rmpt(match, "foo", "bar", mock_db.session(), mock)

    assert mock.mock_calls == []

    assert mock_db.get_data(karma.karma_table) == [
        ("foo", "bar", "some thing", -1)
    ]


def test_re_rmpt_minuspts(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    data = [{"name": "foo", "chan": "#bar", "thing": "baz", "score": -5}]
    for row in data:
        mock_db.add_row(karma.karma_table, **row)

    match = karma.karmaminus_re.search("--")

    mock = MagicMock()
    karma.re_rmpt(match, "foo", "#bar", mock_db.session(), mock)

    assert mock.mock_calls == [call("baz has -5 points ")]


def test_points(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)

    res = karma.points_cmd("baz", "#bar", mock_db.session())

    assert res == "I couldn't find baz in the database."

    data = [
        {"name": "foo", "chan": "#bar", "thing": "baz", "score": -5},
        {"name": "foo", "chan": "#baz", "thing": "baz", "score": 5},
    ]
    for row in data:
        mock_db.add_row(karma.karma_table, **row)

    res = karma.points_cmd("baz", "#bar", mock_db.session())

    assert res == "baz has a total score of -5 (+0/-5) in #bar."

    res = karma.points_cmd("baz global", "#bar", mock_db.session())

    expected = (
        "baz has a total score of 0 (+5/-5) across all channels I know about."
    )
    assert res == expected


def test_pointstop(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    data = [
        {"name": "foo", "chan": "#bar", "thing": "baz", "score": -5,},
        {"name": "foo", "chan": "#baz", "thing": "bing", "score": -1,},
    ]
    for row in data:
        mock_db.add_row(karma.karma_table, **row)

    res = karma.pointstop("", "#bar", mock_db.session())
    assert res == "The 1 most loved things in #bar are: baz with -5 points"

    res = karma.pointstop("global", "#bar", mock_db.session())
    expected = (
        "The 2 most loved things in all channels are: "
        "bing with -1 points • baz with -5 points"
    )

    assert res == expected


def test_pointsbottom(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    res = karma.pointsbottom("global", "#bar", mock_db.session())

    assert res is None

    data = [
        {"name": "foo", "chan": "#bar", "thing": "baz", "score": -5},
        {"name": "foo", "chan": "#baz", "thing": "bing", "score": -1},
    ]
    for row in data:
        mock_db.add_row(karma.karma_table, **row)

    res = karma.pointsbottom("", "#bar", mock_db.session())
    assert res == "The 1 most hated things in #bar are: baz with -5 points"

    res = karma.pointsbottom("global", "#bar", mock_db.session())
    expected = (
        "The 2 most hated things in all channels are: "
        "baz with -5 points • bing with -1 points"
    )

    assert res == expected
