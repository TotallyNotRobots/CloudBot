from unittest.mock import MagicMock

import pytest
import requests
from responses import RequestsMock
from responses.matchers import query_param_matcher

from plugins import horoscope
from tests.util.mock_db import MockDB

BASE_URL = (
    "http://www.horoscope.com/us/horoscopes/general/"
    "horoscope-general-daily-today.aspx"
)

URL = (
    "http://www.horoscope.com/us/horoscopes/general/"
    "horoscope-general-daily-today.aspx?sign={sign}"
)


def setup_db(mock_db):
    horoscope.table.create(mock_db.engine, checkfirst=True)
    sess = mock_db.session()
    sess.execute(horoscope.table.delete())

    return sess


def test_horoscope(mock_requests: RequestsMock, mock_db: MockDB):
    sess = setup_db(mock_db)
    mock_requests.add(
        "GET",
        BASE_URL,
        headers={"User-Agent": "Some user agent"},
        body="""
        <div class="main-horoscope">
            <p>Some horoscope text</p>
        </div>
        """,
        match=[query_param_matcher({"sign": 1})],
    )

    event = MagicMock()
    bot = MagicMock()
    bot.user_agent = "Some user agent"

    response = horoscope.horoscope("aries", sess, bot, "some_user", event)

    assert response is None

    event.message.assert_called_once_with("\x02aries\x02 Some horoscope text")

    assert mock_db.get_data(horoscope.table) == [("some_user", "aries")]


def test_invalid_syntax(mock_requests: RequestsMock, mock_db: MockDB):
    sess = setup_db(mock_db)

    event = MagicMock()
    bot = MagicMock()
    bot.user_agent = "Some user agent"

    response = horoscope.horoscope("", sess, bot, "some_user", event)

    assert response is None

    assert event.notice_doc.call_count == 1


def test_database_read(mock_requests: RequestsMock, mock_db: MockDB):
    sess = setup_db(mock_db)

    mock_requests.add(
        "GET",
        BASE_URL,
        headers={"User-Agent": "Some user agent"},
        body="""
        <div class="main-horoscope">
            <p>Some horoscope text</p>
        </div>
        """,
        match=[query_param_matcher({"sign": 4})],
    )

    mock_db.add_row(horoscope.table, nick="some_user", sign="cancer")

    event = MagicMock()
    bot = MagicMock()
    bot.user_agent = "Some user agent"

    response = horoscope.horoscope("", sess, bot, "some_user", event)

    assert response is None

    event.message.assert_called_once_with("\x02cancer\x02 Some horoscope text")


def test_parse_fail(mock_requests: RequestsMock, mock_db: MockDB):
    sess = setup_db(mock_db)

    mock_requests.add(
        "GET",
        BASE_URL,
        headers={"User-Agent": "Some user agent"},
        body="""
        <div class="main-horoscope">
        </div>
        """,
        match=[query_param_matcher({"sign": 4})],
    )

    event = MagicMock()
    bot = MagicMock()
    bot.user_agent = "Some user agent"

    with pytest.raises(horoscope.HoroscopeParseError):
        horoscope.horoscope("cancer", sess, bot, "some_user", event)

    event.reply.assert_called_once_with("Unable to parse horoscope posting")


def test_page_error(mock_requests: RequestsMock, mock_db: MockDB):
    sess = setup_db(mock_db)

    event = MagicMock()
    bot = MagicMock()
    bot.user_agent = "Some user agent"

    mock_requests.add("GET", URL.format(sign=1), status=404)

    with pytest.raises(requests.RequestException):
        horoscope.horoscope("aries", sess, bot, "some_user", event)

    event.reply.assert_called_once_with(
        "Could not get horoscope: 404 Client Error: Not Found for url: {}. URL Error".format(
            URL.format(sign=1)
        )
    )


def test_bad_sign(mock_requests: RequestsMock):
    db = MagicMock()
    event = MagicMock()
    sign = "some_sign"
    res, err = horoscope.parse_or_lookup(sign, db, "foobar", event)
    assert res is None
    assert err is None
    event.notice.assert_called_with(f"Unknown sign: {sign}")
