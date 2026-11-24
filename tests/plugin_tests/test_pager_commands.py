import importlib
from unittest.mock import MagicMock

import pytest

from cloudbot.event import CommandEvent
from cloudbot.util.pager import CommandPager
from plugins import profile
from tests.util import wrap_hook_response
from tests.util.mock_conn import MockClient


@pytest.mark.parametrize(
    ("plugin_name", "hook_name", "pages_name", "page_type"),
    [
        ("grab", "moregrab", "search_pages", "grabsearch"),
        ("reddit_info", "moremod", "search_pages", "modlist"),
    ],
)
def test_page_commands(
    plugin_name, hook_name, pages_name, page_type, mock_bot
) -> None:
    plugin = importlib.import_module(f"plugins.{plugin_name}")

    hook = getattr(plugin, hook_name)

    pages = getattr(plugin, pages_name)

    conn = MockClient(bot=mock_bot, name="testconn")

    pages.clear()
    no_grabs = f"There are no {page_type} pages to show."
    done = (
        "All pages have been shown. "
        "You can specify a page number or do a new search."
    )
    out_of_range = "Please specify a valid page number between 1 and 2."
    no_number = "Please specify an integer value."

    assert hook("", "#testchannel", conn) == no_grabs

    pages["testconn1"]["#testchannel1"] = CommandPager(["a", "b", "c"])

    assert hook("", "#testchannel", conn) == no_grabs

    pages["testconn"]["#testchannel1"] = CommandPager(["a", "b", "c"])

    assert hook("", "#testchannel", conn) == no_grabs

    pages["testconn1"]["#testchannel"] = CommandPager(["a", "b", "c"])

    assert hook("", "#testchannel", conn) == no_grabs

    pages["testconn"]["#testchannel"] = CommandPager(["a", "b", "c"])

    assert hook("", "#testchannel", conn) == ["a", "b (page 1/2)"]
    assert hook("", "#testchannel", conn) == ["c (page 2/2)"]
    assert hook("", "#testchannel", conn) == [done]

    assert hook("-3", "#testchannel", conn) == [out_of_range]
    assert hook("-2", "#testchannel", conn) == ["a", "b (page 1/2)"]
    assert hook("-1", "#testchannel", conn) == ["c (page 2/2)"]
    assert hook("0", "#testchannel", conn) == [out_of_range]
    assert hook("1", "#testchannel", conn) == ["a", "b (page 1/2)"]
    assert hook("2", "#testchannel", conn) == ["c (page 2/2)"]
    assert hook("3", "#testchannel", conn) == [out_of_range]

    assert hook("a", "#testchannel", conn) == [no_number]


def test_profile_pager() -> None:
    pages = profile.cat_pages

    def call(text, chan, nick):
        conn = MagicMock()
        event = CommandEvent(
            nick=nick,
            channel=chan,
            text=text,
            triggered_command="moreprofile",
            cmd_prefix=".",
            hook=MagicMock(),
            conn=conn,
            bot=conn.bot,
        )
        return wrap_hook_response(profile.moreprofile, event)

    no_grabs = "There are no category pages to show."
    done = (
        "All pages have been shown. "
        "You can specify a page number or do a new search."
    )
    out_of_range = "Please specify a valid page number between 1 and 2."
    no_number = "Please specify an integer value."

    assert call("", "#testchannel", "testuser") == [
        ("message", ("testuser", no_grabs))
    ]

    pages["#testchannel1"]["testuser1"] = CommandPager(["a", "b", "c"])

    assert call("", "#testchannel", "testuser") == [
        ("message", ("testuser", no_grabs))
    ]

    pages["#testchannel"]["testuser1"] = CommandPager(["a", "b", "c"])

    assert call("", "#testchannel", "testuser") == [
        ("message", ("testuser", no_grabs))
    ]

    pages["#testchannel1"]["testuser"] = CommandPager(["a", "b", "c"])

    assert call("", "#testchannel", "testuser") == [
        ("message", ("testuser", no_grabs))
    ]

    pages["#testchannel"]["testuser"] = CommandPager(["a", "b", "c"])

    assert call("", "#testchannel", "testuser") == [
        ("message", ("testuser", "a")),
        ("message", ("testuser", "b (page 1/2)")),
    ]
    assert call("", "#testchannel", "testuser") == [
        ("message", ("testuser", "c (page 2/2)"))
    ]
    assert call("", "#testchannel", "testuser") == [
        ("message", ("testuser", done))
    ]

    assert call("-3", "#testchannel", "testuser") == [
        ("message", ("testuser", out_of_range))
    ]
    assert call("-2", "#testchannel", "testuser") == [
        ("message", ("testuser", "a")),
        ("message", ("testuser", "b (page 1/2)")),
    ]
    assert call("-1", "#testchannel", "testuser") == [
        ("message", ("testuser", "c (page 2/2)"))
    ]
    assert call("0", "#testchannel", "testuser") == [
        ("message", ("testuser", out_of_range))
    ]
    assert call("1", "#testchannel", "testuser") == [
        ("message", ("testuser", "a")),
        ("message", ("testuser", "b (page 1/2)")),
    ]
    assert call("2", "#testchannel", "testuser") == [
        ("message", ("testuser", "c (page 2/2)"))
    ]
    assert call("3", "#testchannel", "testuser") == [
        ("message", ("testuser", out_of_range))
    ]

    assert call("a", "#testchannel", "testuser") == [
        ("message", ("testuser", no_number))
    ]
