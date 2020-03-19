from unittest.mock import MagicMock

import pytest
import requests


def test_shorten(mock_requests):
    from plugins import shorten
    from cloudbot.util import web
    reply = MagicMock()
    with pytest.raises(web.ServiceError):
        shorten.shorten('https://example.com', reply)

    assert reply.called

    mock_requests.add(
        mock_requests.GET,
        'http://is.gd/create.php',
        json={
            'shorturl': 'https://is.gd/foobar'
        }
    )
    assert shorten.shorten('https://example.com', reply) == 'https://is.gd/foobar'


def test_expand(mock_requests):
    from plugins import shorten
    from cloudbot.util import web
    reply = MagicMock()

    with pytest.raises(web.ServiceError):
        shorten.expand('https://is.gd/foobar', reply)

    mock_requests.add(
        mock_requests.GET,
        'http://is.gd/forward.php?shorturl=https%3A%2F%2Fis.gd%2Ffoobar&format=json',
        json={
            'url': 'https://example.com'
        }
    )
    assert shorten.expand('https://is.gd/foobar', reply) == 'https://example.com'


def test_isgd(mock_requests):
    from plugins import shorten
    from cloudbot.util import web
    reply = MagicMock()

    with pytest.raises(web.ServiceError):
        shorten.isgd('https://is.gd/foobar', reply)

    with pytest.raises(web.ServiceError):
        shorten.isgd('https://example.com/page', reply)

    mock_requests.add(
        mock_requests.GET,
        'http://is.gd/forward.php?shorturl=https%3A%2F%2Fis.gd%2Ffoobar&format=json',
        json={
            'url': 'https://example.com'
        }
    )
    assert shorten.isgd('https://is.gd/foobar', reply) == 'https://example.com'

    mock_requests.add(
        mock_requests.GET,
        'http://is.gd/create.php?url=https%3A%2F%2Fexample.com&format=json',
        json={
            'shorturl': 'https://is.gd/foobar'
        }
    )
    assert shorten.isgd('https://example.com', reply) == 'https://is.gd/foobar'


def test_googl(mock_requests):
    from plugins import shorten
    from cloudbot.util import web
    reply = MagicMock()

    with pytest.raises(web.ServiceError):
        shorten.googl('https://goo.gl/foobar', reply)

    with pytest.raises(web.ServiceError):
        shorten.googl('https://example.com/page', reply)

    mock_requests.add(
        mock_requests.GET,
        'https://www.googleapis.com/urlshortener/v1/url?shortUrl=https%3A%2F%2Fgoo.gl%2Ffoobar',
        json={
            'longUrl': 'https://example.com'
        }
    )
    assert shorten.googl('https://goo.gl/foobar', reply) == 'https://example.com'

    mock_requests.add(
        mock_requests.POST,
        'https://www.googleapis.com/urlshortener/v1/url',
        json={
            'id': 'https://goo.gl/foobar'
        }
    )
    assert shorten.googl('https://example.com', reply) == 'https://goo.gl/foobar'


def test_gitio(mock_requests):
    from plugins import shorten
    from cloudbot.util import web
    reply = MagicMock()

    with pytest.raises(web.ServiceError):
        shorten.gitio('https://git.io/foobar', reply)

    with pytest.raises(web.ServiceError):
        shorten.gitio('https://example.com/page', reply)

    mock_requests.add(
        mock_requests.GET,
        'https://git.io/foobar',
        status=301,
        headers={
            'Location': 'https://example.com'
        }
    )
    assert shorten.gitio('https://git.io/foobar', reply) == 'https://example.com'

    mock_requests.add(
        mock_requests.POST,
        'http://git.io',
        headers={
            'Location': 'https://git.io/foobar'
        },
        status=requests.codes.created
    )
    assert shorten.gitio('https://example.com', reply) == 'https://git.io/foobar'
