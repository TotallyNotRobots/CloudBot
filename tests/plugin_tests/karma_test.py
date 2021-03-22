from plugins import karma


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
