from typing import List
from unittest.mock import MagicMock

import pytest
from requests import RequestException

from cloudbot.event import CommandEvent
from plugins import wikipedia
from tests.util import HookResult, wrap_hook_response


def do_search(query, results=None):
    conn = MagicMock()
    conn.config = {}
    conn.bot = None

    cmd_event = CommandEvent(
        text=query,
        cmd_prefix=".",
        triggered_command="wiki",
        hook=MagicMock(),
        bot=conn.bot,
        conn=conn,
        channel="#foo",
        nick="foobaruser",
    )

    return wrap_hook_response(wikipedia.wiki, cmd_event, results=results)


def make_search_url(query):
    query = query.replace(" ", "+")
    return (
        "http://en.wikipedia.org/w/api.php?action=query&format=json&list=search"
        "&redirect=1&srsearch=" + query
    )


def test_search(mock_requests):
    err_results: List[HookResult] = []
    with pytest.raises(RequestException):
        do_search("some failed query", err_results)

    assert err_results == [
        ("message", ("#foo", "(foobaruser) Could not get Wikipedia page"))
    ]

    mock_requests.add(
        "GET", make_search_url("some search"), json={"query": {"search": []}}
    )

    results = do_search("some search")

    assert results == [("return", "No results found.")]

    mock_requests.add(
        "GET",
        make_search_url("a search"),
        json={
            "query": {
                "search": [
                    {"title": "Other title"},
                    {
                        "title": "A title",
                    },
                ]
            }
        },
    )

    mock_requests.add(
        "GET",
        wikipedia.make_summary_url("Other title"),
        json={"type": "nonstandard"},
    )

    mock_requests.add(
        "GET",
        wikipedia.make_summary_url("A title"),
        json={
            "type": "standard",
            "extract": "Some description",
            "content_urls": {"desktop": {"page": "Some url"}},
        },
    )

    results = do_search("a search")

    assert results == [("return", "A title :: Some description :: Some url")]

    mock_requests.replace(
        "GET",
        wikipedia.make_summary_url("A title"),
        json={
            "type": "standard",
            "extract": "",
            "content_urls": {"desktop": {"page": "Some url"}},
        },
    )

    results = do_search("a search")

    assert results == [("return", "A title :: (No Summary) :: Some url")]
