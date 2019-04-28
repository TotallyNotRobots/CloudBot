import importlib

import pytest

from cloudbot.util.pager import Pager


class MockConn:
    def __init__(self, name):
        self.name = name


@pytest.mark.parametrize('plugin_name,hook_name,pages_name,page_type', [
    ['grab', 'moregrab', 'search_pages', 'grabsearch'],
    ['reddit_info', 'moremod', 'search_pages', 'modlist'],
    ['sportscores', 'morescore', 'search_pages', 'score'],
])
def test_page_commands(plugin_name, hook_name, pages_name, page_type):
    plugin = importlib.import_module('plugins.' + plugin_name)

    hook = getattr(plugin, hook_name)

    pages = getattr(plugin, pages_name)

    conn = MockConn('testconn')

    no_grabs = "There are no {} pages to show.".format(page_type)
    done = "All pages have been shown. " \
           "You can specify a page number or do a new search."
    out_of_range = "Please specify a valid page number between 1 and 2."
    no_number = "Please specify an integer value."

    assert hook('', '#testchannel', conn) == no_grabs

    pages['testconn1']['#testchannel1'] = Pager(['a', 'b', 'c'])

    assert hook('', '#testchannel', conn) == no_grabs

    pages['testconn']['#testchannel1'] = Pager(['a', 'b', 'c'])

    assert hook('', '#testchannel', conn) == no_grabs

    pages['testconn1']['#testchannel'] = Pager(['a', 'b', 'c'])

    assert hook('', '#testchannel', conn) == no_grabs

    pages['testconn']['#testchannel'] = Pager(['a', 'b', 'c'])

    assert hook('', '#testchannel', conn) == ['a', 'b (page 1/2)']
    assert hook('', '#testchannel', conn) == ['c (page 2/2)']
    assert hook('', '#testchannel', conn) == done

    assert hook('1', '#testchannel', conn) == ['a', 'b (page 1/2)']
    assert hook('2', '#testchannel', conn) == ['c (page 2/2)']
    assert hook('3', '#testchannel', conn) == out_of_range

    assert hook('a', '#testchannel', conn) == no_number
