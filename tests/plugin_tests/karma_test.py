from unittest.mock import MagicMock, call

from plugins import karma
from tests.util.mock_db import MockDB


def test_db_clean(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    mock_db.add_row(
        karma.karma_table, name="foo", chan="bar", thing="baz", score=50
    )
    mock_db.add_row(
        karma.karma_table, name="foo", chan="#bar", thing="baz", score=50
    )
    db = mock_db.session()
    karma.remove_non_channel_points(db)
    assert mock_db.get_data(karma.karma_table) == [("foo", "#bar", "baz", 50)]


def test_update_score(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    karma.update_score("foo", "#bar", "thing", 1, db)
    assert mock_db.get_data(karma.karma_table) == [("foo", "#bar", "thing", 1)]
    karma.update_score("foo", "#bar", "thing", 1, db)
    assert mock_db.get_data(karma.karma_table) == [("foo", "#bar", "thing", 2)]
    karma.update_score("foo", "#bar", "thing", -1, db)
    assert mock_db.get_data(karma.karma_table) == [("foo", "#bar", "thing", 1)]


def test_update_score_in_pm(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    karma.update_score("foo", "foo", "thing", 1, db)
    assert mock_db.get_data(karma.karma_table) == []


def test_addpoint(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    karma.addpoint("foo", "foo", "#bar", db)
    assert mock_db.get_data(karma.karma_table) == [
        ("foo", "#bar", "foo", 1),
    ]


def test_re_addpt(mock_db: MockDB):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    match = karma.karmaplus_re.search("foo++")
    notice = MagicMock()
    karma.re_addpt(match, "testnick", "#chan", db, notice)
    assert notice.mock_calls == []
    assert mock_db.get_data(karma.karma_table) == [
        ("testnick", "#chan", "foo", 1),
    ]


def test_re_addpt_empty_get(mock_db: MockDB):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    match = karma.karmaplus_re.search("++")
    notice = MagicMock()
    karma.re_addpt(match, "testnick", "#chan", db, notice)
    assert notice.mock_calls == []
    assert mock_db.get_data(karma.karma_table) == []


def test_re_addpt_single_get(mock_db: MockDB):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    mock_db.load_data(
        karma.karma_table,
        [
            {"name": "testnick", "thing": "foo", "chan": "#chan", "score": 4},
        ],
    )
    db = mock_db.session()
    match = karma.karmaplus_re.search("++")
    notice = MagicMock()
    karma.re_addpt(match, "testnick", "#chan", db, notice)
    assert notice.mock_calls == [call("foo has 4 points ")]
    assert mock_db.get_data(karma.karma_table) == [
        ("testnick", "#chan", "foo", 4)
    ]


def test_re_addpt_multi_get(mock_db: MockDB):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    mock_db.load_data(
        karma.karma_table,
        [
            {"name": "testnick", "thing": "foo", "chan": "#chan", "score": 4},
            {"name": "testnick2", "thing": "foo", "chan": "#chan", "score": 4},
            {"name": "testnick3", "thing": "foo", "chan": "#chan", "score": -4},
            {"name": "testnick", "thing": "foo2", "chan": "#chan", "score": 4},
            {"name": "testnick", "thing": "foo3", "chan": "#chan", "score": -4},
        ],
    )

    db = mock_db.session()
    match = karma.karmaplus_re.search("++")
    notice = MagicMock()
    karma.re_addpt(match, "testnick", "#chan", db, notice)
    assert notice.mock_calls == [call("foo has 4 points foo2 has 4 points ")]


def test_re_rmpt(mock_db: MockDB):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    match = karma.karmaminus_re.search("foo--")
    notice = MagicMock()
    karma.re_rmpt(match, "testnick", "#chan", db, notice)
    assert notice.mock_calls == []
    assert mock_db.get_data(karma.karma_table) == [
        ("testnick", "#chan", "foo", -1),
    ]


def test_re_rmpt_empty_get(mock_db: MockDB):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    match = karma.karmaminus_re.search("--")
    notice = MagicMock()
    karma.re_rmpt(match, "testnick", "#chan", db, notice)
    assert notice.mock_calls == []
    assert mock_db.get_data(karma.karma_table) == []


def test_re_rmpt_single_get(mock_db: MockDB):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    mock_db.load_data(
        karma.karma_table,
        [
            {"name": "testnick", "thing": "foo", "chan": "#chan", "score": -4},
        ],
    )

    db = mock_db.session()
    match = karma.karmaminus_re.search("--")
    notice = MagicMock()
    karma.re_rmpt(match, "testnick", "#chan", db, notice)
    assert notice.mock_calls == [call("foo has -4 points ")]


def test_re_rmpt_multi_get(mock_db: MockDB):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    mock_db.load_data(
        karma.karma_table,
        [
            {"name": "testnick", "thing": "foo", "chan": "#chan", "score": -4},
            {"name": "testnick2", "thing": "foo", "chan": "#chan", "score": -4},
            {"name": "testnick3", "thing": "foo", "chan": "#chan", "score": 4},
            {"name": "testnick", "thing": "foo2", "chan": "#chan", "score": -4},
            {"name": "testnick", "thing": "foo3", "chan": "#chan", "score": 4},
        ],
    )
    db = mock_db.session()
    match = karma.karmaminus_re.search("--")
    notice = MagicMock()
    karma.re_rmpt(match, "testnick", "#chan", db, notice)
    assert notice.mock_calls == [call("foo has -4 points foo2 has -4 points ")]


def test_pointstop(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    chan = "#bar"
    karma.update_score("foo", chan, "thing", 1, db)
    res = karma.pointstop("", chan, db)
    assert res == "The 1 most loved things in #bar are: thing with 1 points"


def test_pointstop_empty(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    chan = "#bar"
    res = karma.pointstop("", chan, db)
    assert res is None


def test_pointstop_global_multi(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    chan = "#bar"
    karma.update_score("foo", chan, "thing", 1, db)
    karma.update_score("foo", chan + "1", "thing", 1, db)
    karma.update_score("foo", chan + "1", "thing1", 1, db)
    res = karma.pointstop("global", chan, db)
    assert res == (
        "The 2 most loved things in all channels are: thing with 2 points • thing1 "
        "with 1 points"
    )


def test_pointstop_global(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    chan = "#bar"
    karma.update_score("foo", chan, "thing", 1, db)
    res = karma.pointstop("global", chan, db)
    assert (
        res
        == "The 1 most loved things in all channels are: thing with 1 points"
    )


def test_pointstop_global_other_chan(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    chan = "#bar"
    karma.update_score("foo", chan, "thing", 1, db)
    res = karma.pointstop("global", chan + "1", db)
    assert (
        res
        == "The 1 most loved things in all channels are: thing with 1 points"
    )


def test_pointstop_global_empty(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    chan = "#bar"
    res = karma.pointstop("global", chan, db)
    assert res is None


def test_pointsbottom(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    chan = "#bar"
    karma.update_score("foo", chan, "thing", 1, db)
    res = karma.pointsbottom("", chan, db)
    assert res == "The 1 most hated things in #bar are: thing with 1 points"


def test_pointsbottom_empty(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    chan = "#bar"
    res = karma.pointsbottom("", chan, db)
    assert res is None


def test_pointsbottom_global_multi(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    chan = "#bar"
    karma.update_score("foo", chan, "thing", 1, db)
    karma.update_score("foo", chan + "1", "thing", 1, db)
    karma.update_score("foo", chan + "1", "thing1", 1, db)
    res = karma.pointsbottom("global", chan, db)
    assert res == (
        "The 2 most hated things in all channels are: thing1 with 1 points • thing with 2 points"
    )


def test_pointsbottom_global(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    chan = "#bar"
    karma.update_score("foo", chan, "thing", 1, db)
    res = karma.pointsbottom("global", chan, db)
    assert (
        res
        == "The 1 most hated things in all channels are: thing with 1 points"
    )


def test_pointsbottom_global_other_chan(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    chan = "#bar"
    karma.update_score("foo", chan, "thing", 1, db)
    res = karma.pointsbottom("global", chan + "1", db)
    assert (
        res
        == "The 1 most hated things in all channels are: thing with 1 points"
    )


def test_pointsbottom_global_empty(mock_db):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    db = mock_db.session()
    chan = "#bar"
    res = karma.pointsbottom("global", chan, db)
    assert res is None


def test_points_cmd_unknown(mock_db: MockDB):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    mock_db.load_data(
        karma.karma_table,
        [
            {"name": "testnick", "thing": "foo", "chan": "#chan", "score": -4},
            {"name": "testnick2", "thing": "foo", "chan": "#chan", "score": -4},
            {"name": "testnick3", "thing": "foo", "chan": "#chan", "score": 4},
            {"name": "testnick", "thing": "foo2", "chan": "#chan", "score": -4},
            {"name": "testnick", "thing": "foo3", "chan": "#chan", "score": 4},
        ],
    )

    db = mock_db.session()
    res = karma.points_cmd("unknown", "#chan", db)
    assert res == "I couldn't find unknown in the database."


def test_points_cmd_basic(mock_db: MockDB):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    mock_db.load_data(
        karma.karma_table,
        [
            {"name": "testnick", "thing": "foo", "chan": "#chan", "score": -4},
            {"name": "testnick2", "thing": "foo", "chan": "#chan", "score": -4},
            {"name": "testnick3", "thing": "foo", "chan": "#chan", "score": 4},
            {"name": "testnick", "thing": "foo2", "chan": "#chan", "score": -4},
            {"name": "testnick", "thing": "foo3", "chan": "#chan", "score": 4},
        ],
    )

    db = mock_db.session()
    res = karma.points_cmd("foo", "#chan", db)
    assert res == "foo has a total score of -4 (+4/-8) in #chan."


def test_points_cmd_global(mock_db: MockDB):
    karma.karma_table.create(mock_db.engine, checkfirst=True)
    mock_db.load_data(
        karma.karma_table,
        [
            {"name": "testnick", "thing": "foo", "chan": "#chan", "score": -4},
            {"name": "testnick2", "thing": "foo", "chan": "#chan", "score": -4},
            {"name": "testnick3", "thing": "foo", "chan": "#chan", "score": 4},
            {"name": "testnick", "thing": "foo2", "chan": "#chan", "score": -4},
            {"name": "testnick3", "thing": "foo", "chan": "#chan2", "score": 7},
            {"name": "testnick", "thing": "foo3", "chan": "#chan", "score": 4},
        ],
    )

    db = mock_db.session()
    res = karma.points_cmd("foo global", "#chan", db)
    assert (
        res
        == "foo has a total score of 3 (+11/-8) across all channels I know about."
    )
