import importlib

import pytest

from cloudbot.util import web
from plugins.pastebins import sprunge


def test_register():
    importlib.reload(web)
    importlib.reload(sprunge)

    sprunge.register()

    assert web.pastebins.get('sprunge') is not None

    sprunge.unregister()

    assert web.pastebins.get('sprunge') is None


def test_paste(mock_requests):
    importlib.reload(web)
    importlib.reload(sprunge)

    sprunge.register()

    paster = web.pastebins['sprunge']

    mock_requests.add(
        'POST', 'http://sprunge.us', body='http://sprunge.us/foobar'
    )
    assert paster.paste('test data', 'txt') == 'http://sprunge.us/foobar?txt'


def test_paste_bytes(mock_requests):
    importlib.reload(web)
    importlib.reload(sprunge)

    sprunge.register()

    paster = web.pastebins['sprunge']

    mock_requests.add(
        'POST', 'http://sprunge.us', body='http://sprunge.us/foobar'
    )
    assert paster.paste(b'test data', 'txt') == 'http://sprunge.us/foobar?txt'


def test_paste_error(mock_requests):
    importlib.reload(web)
    importlib.reload(sprunge)

    sprunge.register()

    paster = web.pastebins['sprunge']

    with pytest.raises(web.ServiceError):
        paster.paste('test data', 'txt')

    mock_requests.add(
        'POST', 'http://sprunge.us', status=500,
    )

    with pytest.raises(web.ServiceHTTPError):
        paster.paste('test data', 'txt')
