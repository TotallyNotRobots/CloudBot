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
