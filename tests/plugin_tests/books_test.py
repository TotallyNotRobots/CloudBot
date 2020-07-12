import importlib

import pytest
from requests import HTTPError

from plugins import books
from tests.util import run_cmd


def test_books_no_api(mock_requests, mock_api_keys):
    importlib.reload(books)
    mock_api_keys.return_value = None
    assert run_cmd(books.books, "books", "foobar") == [
        ("return", "This command requires a Google Developers Console API key.")
    ]


def test_books_http_error(mock_api_keys, mock_requests):
    importlib.reload(books)
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foobar&key=APIKEY"
        "&country=US",
        match_querystring=True,
        status=404,
    )
    res = []

    with pytest.raises(HTTPError):
        run_cmd(books.books, "books", "foobar", results=res)

    assert res == [("message", ("#foo", "(foonick) Books API error occurred."))]


def test_books_api_off(mock_api_keys, mock_requests):
    importlib.reload(books)
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foobar&key=APIKEY"
        "&country=US",
        match_querystring=True,
        json={"error": {"code": 403}},
    )
    assert run_cmd(books.books, "books", "foobar") == [
        (
            "return",
            "The Books API is off in the Google Developers Console (or check "
            "the console).",
        )
    ]


def test_books_api_error(mock_api_keys, mock_requests):
    importlib.reload(books)
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foobar&key=APIKEY"
        "&country=US",
        match_querystring=True,
        json={"error": {"code": 400}},
    )
    assert run_cmd(books.books, "books", "foobar") == [
        ("return", "Error performing search.")
    ]


def test_books_no_results(mock_requests, mock_api_keys):
    importlib.reload(books)
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foobar&key=APIKEY"
        "&country=US",
        match_querystring=True,
        json={"totalItems": 0,},
    )
    assert run_cmd(books.books, "books", "foobar") == [
        ("return", "No results found.")
    ]


def test_books(mock_requests, mock_api_keys):
    importlib.reload(books)
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foobar&key=APIKEY"
        "&country=US",
        match_querystring=True,
        json={
            "totalItems": 1,
            "items": [
                {
                    "volumeInfo": {
                        "title": "foobarbaz",
                        "infoLink": "host.invalid",
                    },
                }
            ],
        },
    )
    assert run_cmd(books.books, "books", "foobar") == [
        (
            "return",
            "\x02foobarbaz\x02 by \x02Unknown Author\x02 (No Year) - No "
            "description available. - host.invalid",
        )
    ]


def test_books_authors(mock_requests, mock_api_keys):
    importlib.reload(books)
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foobar&key=APIKEY"
        "&country=US",
        match_querystring=True,
        json={
            "totalItems": 1,
            "items": [
                {
                    "volumeInfo": {
                        "title": "foobarbaz",
                        "infoLink": "host.invalid",
                        "authors": ["fred"],
                    },
                }
            ],
        },
    )

    assert run_cmd(books.books, "books", "foobar") == [
        (
            "return",
            "\x02foobarbaz\x02 by \x02fred\x02 (No Year) - No description "
            "available. - host.invalid",
        )
    ]


def test_books_multiple_authors(mock_requests, mock_api_keys):
    importlib.reload(books)
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foobar&key=APIKEY"
        "&country=US",
        match_querystring=True,
        json={
            "totalItems": 1,
            "items": [
                {
                    "volumeInfo": {
                        "title": "foobarbaz",
                        "infoLink": "host.invalid",
                        "authors": ["fred", "george"],
                    },
                }
            ],
        },
    )

    assert run_cmd(books.books, "books", "foobar") == [
        (
            "return",
            "\x02foobarbaz\x02 by \x02fred\x02 (No Year) - No description "
            "available. - host.invalid",
        )
    ]


def test_books_publisher(mock_requests, mock_api_keys):
    importlib.reload(books)
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foobar&key=APIKEY"
        "&country=US",
        match_querystring=True,
        json={
            "totalItems": 1,
            "items": [
                {
                    "volumeInfo": {
                        "title": "foobarbaz",
                        "infoLink": "host.invalid",
                        "publisher": "publisher",
                    },
                }
            ],
        },
    )

    assert run_cmd(books.books, "books", "foobar") == [
        (
            "return",
            "\x02foobarbaz\x02 by \x02publisher\x02 (No Year) - No "
            "description available. - host.invalid",
        )
    ]


def test_books_page_count(mock_requests, mock_api_keys):
    importlib.reload(books)
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foobar&key=APIKEY"
        "&country=US",
        match_querystring=True,
        json={
            "totalItems": 1,
            "items": [
                {
                    "volumeInfo": {
                        "title": "foobarbaz",
                        "infoLink": "host.invalid",
                        "publisher": "publisher",
                        "pageCount": 42,
                    },
                }
            ],
        },
    )

    assert run_cmd(books.books, "books", "foobar") == [
        (
            "return",
            "\x02foobarbaz\x02 by \x02publisher\x02 (No Year) - \x0242\x02 "
            "pages - No description available. - host.invalid",
        )
    ]


def test_books_description_short(mock_requests, mock_api_keys):
    importlib.reload(books)
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foobar&key=APIKEY"
        "&country=US",
        match_querystring=True,
        json={
            "totalItems": 1,
            "items": [
                {
                    "volumeInfo": {
                        "title": "foobarbaz",
                        "infoLink": "host.invalid",
                        "publisher": "publisher",
                        "pageCount": 42,
                        "description": "a" * 100,
                    },
                }
            ],
        },
    )

    assert run_cmd(books.books, "books", "foobar") == [
        (
            "return",
            "\x02foobarbaz\x02 by \x02publisher\x02 (No Year) - \x0242\x02 "
            "pages - aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            "aaaaaaaaa - host.invalid",
        )
    ]


def test_books_description_long(mock_requests, mock_api_keys):
    importlib.reload(books)
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/books/v1/volumes?q=foobar&key=APIKEY"
        "&country=US",
        match_querystring=True,
        json={
            "totalItems": 1,
            "items": [
                {
                    "volumeInfo": {
                        "title": "foobarbaz",
                        "infoLink": "host.invalid",
                        "publisher": "publisher",
                        "pageCount": 42,
                        "description": "a" * 200,
                    },
                }
            ],
        },
    )

    assert run_cmd(books.books, "books", "foobar") == [
        (
            "return",
            "\x02foobarbaz\x02 by \x02publisher\x02 (No Year) - \x0242\x02 "
            "pages - "
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            "aaaa... - host.invalid",
        )
    ]
