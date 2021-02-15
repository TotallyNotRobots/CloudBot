from unittest.mock import MagicMock

from plugins import cats


def test_cats(mock_requests):
    mock_requests.add(
        "GET",
        "https://catfact.ninja/fact?max_length=100",
        json={"fact": "foobar"},
    )
    bot = MagicMock(user_agent="user agent")
    reply = MagicMock()
    assert cats.cats(reply, bot) == "foobar"
    assert bot.mock_calls == []
    assert reply.mock_calls == []


def test_catgifs(mock_requests):
    url = "https://foobar/"
    mock_requests.add("GET", url)
    mock_requests.add(
        "GET",
        "http://marume.herokuapp.com/random.gif",
        status=301,
        adding_headers={"Location": url},
    )
    bot = MagicMock(user_agent="user agent")
    reply = MagicMock()
    assert cats.catgifs(reply, bot) == ("OMG A CAT GIF: " + url)
    assert bot.mock_calls == []
    assert reply.mock_calls == []
