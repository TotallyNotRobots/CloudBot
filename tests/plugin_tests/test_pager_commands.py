import importlib

import pytest

from cloudbot.util.pager import CommandPager
from plugins import profile


class MockConn:
    def __init__(self, name):
        self.name = name


@pytest.mark.parametrize(
    "plugin_name,hook_name,pages_name,page_type",
    [
        ["grab", "moregrab", "search_pages", "grabsearch"],
        ["reddit_info", "moremod", "search_pages", "modlist"],
        ["sportscores", "morescore", "search_pages", "score"],
    ],
)
def test_page_commands(plugin_name, hook_name, pages_name, page_type):
    plugin = importlib.import_module("plugins." + plugin_name)

    hook = getattr(plugin, hook_name)

    pages = getattr(plugin, pages_name)

    conn = MockConn("testconn")

    pages.clear()
    no_grabs = "There are no {} pages to show.".format(page_type)
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


class CaptureCalls:
    def __init__(self):
        self.lines = []

    def __call__(self, text):
        self.lines.append(text)


def test_profile_pager():
    hook = profile.moreprofile

    pages = profile.cat_pages

    def call(*args):
        notice = CaptureCalls()
        hook(*args, notice=notice)
        return notice.lines

    no_grabs = "There are no category pages to show."
    done = (
        "All pages have been shown. "
        "You can specify a page number or do a new search."
    )
    out_of_range = "Please specify a valid page number between 1 and 2."
    no_number = "Please specify an integer value."

    assert call("", "#testchannel", "testuser") == [no_grabs]

    pages["#testchannel1"]["testuser1"] = CommandPager(["a", "b", "c"])

    assert call("", "#testchannel", "testuser") == [no_grabs]

    pages["#testchannel"]["testuser1"] = CommandPager(["a", "b", "c"])

    assert call("", "#testchannel", "testuser") == [no_grabs]

    pages["#testchannel1"]["testuser"] = CommandPager(["a", "b", "c"])

    assert call("", "#testchannel", "testuser") == [no_grabs]

    pages["#testchannel"]["testuser"] = CommandPager(["a", "b", "c"])

    assert call("", "#testchannel", "testuser") == ["a", "b (page 1/2)"]
    assert call("", "#testchannel", "testuser") == ["c (page 2/2)"]
    assert call("", "#testchannel", "testuser") == [done]

    assert call("-3", "#testchannel", "testuser") == [out_of_range]
    assert call("-2", "#testchannel", "testuser") == ["a", "b (page 1/2)"]
    assert call("-1", "#testchannel", "testuser") == ["c (page 2/2)"]
    assert call("0", "#testchannel", "testuser") == [out_of_range]
    assert call("1", "#testchannel", "testuser") == ["a", "b (page 1/2)"]
    assert call("2", "#testchannel", "testuser") == ["c (page 2/2)"]
    assert call("3", "#testchannel", "testuser") == [out_of_range]

    assert call("a", "#testchannel", "testuser") == [no_number]
