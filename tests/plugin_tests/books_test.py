from unittest.mock import MagicMock, call

import pytest
import requests

from plugins import books


def test_no_key(mock_bot, mock_requests):
    event = MagicMock()
    res = books.books("foo", event.reply, mock_bot)
    assert res == "This command requires a Google Developers Console API key."
    assert event.mock_calls == []


def test_books_no_results(mock_bot, mock_requests):
    mock_bot.config["api_keys"] = {"google_dev_key": "foo"}
    event = MagicMock()
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foo&key=foo&country=US",
        json={"totalItems": 0},
    )
    res = books.books("foo", event.reply, mock_bot)
    assert res == "No results found."
    assert event.mock_calls == []


def test_books_error_code(mock_bot, mock_requests):
    mock_bot.config["api_keys"] = {"google_dev_key": "foo"}
    event = MagicMock()
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foo&key=foo&country=US",
        status=404,
    )
    with pytest.raises(requests.HTTPError):
        books.books("foo", event.reply, mock_bot)

    assert event.mock_calls == [call.reply("API error occurred.")]


def test_books_error(mock_bot, mock_requests):
    mock_bot.config["api_keys"] = {"google_dev_key": "foo"}
    event = MagicMock()
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foo&key=foo&country=US",
        json={"error": {"code": 404}},
    )
    res = books.books("foo", event.reply, mock_bot)
    assert res == "Error performing search."
    assert event.mock_calls == []


def test_books_error_api_off(mock_bot, mock_requests):
    mock_bot.config["api_keys"] = {"google_dev_key": "foo"}
    event = MagicMock()
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foo&key=foo&country=US",
        json={"error": {"code": 403}},
    )
    res = books.books("foo", event.reply, mock_bot)
    assert (
        res
        == "The Books API is off in the Google Developers Console (or check the console)."
    )
    assert event.mock_calls == []


def test_books(mock_bot, mock_requests, patch_try_shorten):
    mock_bot.config["api_keys"] = {"google_dev_key": "foo"}
    event = MagicMock()
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foo&key=foo&country=US",
        json={
            "totalItems": 1,
            "items": [
                {
                    "volumeInfo": {
                        "title": "foo",
                        "infoLink": "foo.bar",
                        "authors": ["foo", "bar"],
                        "publisher": "test publisher",
                        "description": "foobar",
                        "publishedDate": "2020-07-05",
                        "pageCount": 5,
                    }
                }
            ],
        },
    )
    res = books.books("foo", event.reply, mock_bot)
    assert res == (
        "\x02foo\x02 by \x02foo\x02 (2020) - 5 pages - foobar - foo.bar"
    )
    assert event.mock_calls == []


def test_books_no_authors(mock_bot, mock_requests, patch_try_shorten):
    mock_bot.config["api_keys"] = {"google_dev_key": "foo"}
    event = MagicMock()
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foo&key=foo&country=US",
        json={
            "totalItems": 1,
            "items": [
                {
                    "volumeInfo": {
                        "title": "foo",
                        "infoLink": "foo.bar",
                        "publisher": "test publisher",
                        "description": "foobar",
                        "publishedDate": "2020-07-05",
                        "pageCount": 5,
                    }
                }
            ],
        },
    )
    res = books.books("foo", event.reply, mock_bot)
    assert res == (
        "\x02foo\x02 by \x02test publisher\x02 (2020) - 5 pages - foobar - foo.bar"
    )
    assert event.mock_calls == []


def test_books_no_desc(mock_bot, mock_requests, patch_try_shorten):
    mock_bot.config["api_keys"] = {"google_dev_key": "foo"}
    event = MagicMock()
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foo&key=foo&country=US",
        json={
            "totalItems": 1,
            "items": [
                {
                    "volumeInfo": {
                        "title": "foo",
                        "infoLink": "foo.bar",
                        "authors": ["foo", "bar"],
                        "publisher": "test publisher",
                        "publishedDate": "2020-07-05",
                        "pageCount": 5,
                    }
                }
            ],
        },
    )
    res = books.books("foo", event.reply, mock_bot)
    assert res == (
        "\x02foo\x02 by \x02foo\x02 (2020) - 5 pages - No description available. - "
        "foo.bar"
    )
    assert event.mock_calls == []


def test_books_no_pagecount(mock_bot, mock_requests, patch_try_shorten):
    mock_bot.config["api_keys"] = {"google_dev_key": "foo"}
    event = MagicMock()
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foo&key=foo&country=US",
        json={
            "totalItems": 1,
            "items": [
                {
                    "volumeInfo": {
                        "title": "foo",
                        "infoLink": "foo.bar",
                        "authors": ["foo", "bar"],
                        "publisher": "test publisher",
                        "description": "foobar",
                        "publishedDate": "2020-07-05",
                    }
                }
            ],
        },
    )
    res = books.books("foo", event.reply, mock_bot)
    assert res == ("\x02foo\x02 by \x02foo\x02 (2020) - foobar - foo.bar")
    assert event.mock_calls == []


def test_books_no_author_or_publisher(
    mock_bot, mock_requests, patch_try_shorten
):
    mock_bot.config["api_keys"] = {"google_dev_key": "foo"}
    event = MagicMock()
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foo&key=foo&country=US",
        json={
            "totalItems": 1,
            "items": [
                {
                    "volumeInfo": {
                        "title": "foo",
                        "infoLink": "foo.bar",
                        "description": "foobar",
                        "publishedDate": "2020-07-05",
                        "pageCount": 5,
                    }
                }
            ],
        },
    )
    res = books.books("foo", event.reply, mock_bot)
    assert res == (
        "\x02foo\x02 by \x02Unknown Author\x02 (2020) - 5 pages - foobar - foo.bar"
    )
    assert event.mock_calls == []


def test_books_no_date(mock_bot, mock_requests, patch_try_shorten):
    mock_bot.config["api_keys"] = {"google_dev_key": "foo"}
    event = MagicMock()
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foo&key=foo&country=US",
        json={
            "totalItems": 1,
            "items": [
                {
                    "volumeInfo": {
                        "title": "foo",
                        "infoLink": "foo.bar",
                        "authors": ["foo", "bar"],
                        "publisher": "test publisher",
                        "description": "foobar",
                        "pageCount": 5,
                    }
                }
            ],
        },
    )
    res = books.books("foo", event.reply, mock_bot)
    assert res == (
        "\x02foo\x02 by \x02foo\x02 (No Year) - 5 pages - foobar - foo.bar"
    )
    assert event.mock_calls == []
