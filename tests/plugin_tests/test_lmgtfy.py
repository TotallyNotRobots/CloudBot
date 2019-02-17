import mock
import pytest


@pytest.fixture()
def patch_try_shorten():
    with mock.patch('cloudbot.util.web.try_shorten', new=lambda x: x):
        yield


def test_lmgtfy(patch_try_shorten):
    from plugins.lmgtfy import lmgtfy
    assert lmgtfy('foo bar') == 'http://lmgtfy.com/?q=foo%20bar'
