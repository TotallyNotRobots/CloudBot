from collections import defaultdict, deque
from unittest.mock import MagicMock

from plugins import grab


def test_grab(mock_db):
    grab.table.create(mock_db.engine, checkfirst=True)

    conn = MagicMock()
    conn.mock_add_spec(["name", "history"])
    history = defaultdict(lambda: deque(maxlen=100))
    conn.history = history

    res = grab.grab("foo", "bar", "#baz", mock_db.session(), conn)
    assert res == "I couldn't find anything from foo in recent history."

    history["#baz"].append(("foo", 123, "blah"))

    res = grab.grab("foo", "bar", "#baz", mock_db.session(), conn)
    assert res == "the operation succeeded."

    assert mock_db.get_data(grab.table) == [("foo", "123", "blah", "#baz")]

    history["#baz"].append(("foo", 1234, "blah234"))

    res = grab.grab("foo", "bar", "#baz", mock_db.session(), conn)
    assert res == "the operation succeeded."

    assert mock_db.get_data(grab.table) == [
        ("foo", "123", "blah", "#baz"),
        ("foo", "1234", "blah234", "#baz"),
    ]

    history["#baz"].append(("foo1", 12345, "blah6"))

    res = grab.grab("foo", "bar", "#baz", mock_db.session(), conn)
    assert res == "I already have that quote from foo in the database"

    assert mock_db.get_data(grab.table) == [
        ("foo", "123", "blah", "#baz"),
        ("foo", "1234", "blah234", "#baz"),
    ]

    assert grab.grabsearch("foo", "#baz", conn) == [
        "<f\u200boo> blah • <f\u200boo> blah234"
    ]
