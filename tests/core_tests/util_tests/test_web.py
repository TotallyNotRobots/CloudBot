import datetime
import importlib

import pytest
import requests


def test_paste(mock_requests):
    mock_requests.add(
        mock_requests.POST,
        "https://hastebin.com/documents",
        json={"key": "foobar"},
    )
    from cloudbot.util import web

    assert (
        web.paste("test data", service="hastebin")
        == "https://hastebin.com/foobar.txt"
    )

    assert web.paste("test data", service="none") == "Unable to paste data"


def test_paste_error(mock_requests):
    from cloudbot.util import web

    assert web.paste("test data") == "Unable to paste data"

    mock_requests.add(
        mock_requests.POST, "https://hastebin.com/documents", status=502
    )
    assert web.paste("test data") == "Unable to paste data"

    mock_requests.replace(
        mock_requests.POST,
        "https://hastebin.com/documents",
        json={"message": "Error"},
        status=201,
    )
    assert web.paste("test data") == "Unable to paste data"


def test_registry_item_working(freeze_time):
    from cloudbot.util.web import Registry

    registry = Registry()
    registry.register("test", object())
    item = registry.get_item("test")
    assert item.should_use

    item.failed()
    assert not item.should_use

    freeze_time.tick(datetime.timedelta(minutes=6))

    assert item.should_use


def test_shorten(mock_requests):
    mock_requests.add(
        mock_requests.GET,
        "http://is.gd/create.php",
        json={"shorturl": "https://is.gd/foobar"},
    )
    from cloudbot.util import web

    assert (
        web.shorten("https://example.com", service="is.gd")
        == "https://is.gd/foobar"
    )

    assert (
        web.Shortener().shorten("https://example.com") == "https://example.com"
    )

    with pytest.raises(web.ServiceError):
        web.shorten("https://example.com", service="goo.gl")

    mock_requests.add(
        mock_requests.POST,
        "https://www.googleapis.com/urlshortener/v1/url",
        json={},
        status=requests.codes.bad_request,
    )
    with pytest.raises(web.ServiceHTTPError):
        web.shorten("https://example.com", service="goo.gl")

    mock_requests.replace(
        mock_requests.POST,
        "https://www.googleapis.com/urlshortener/v1/url",
        json={"error": {"message": "Error"}},
    )
    with pytest.raises(web.ServiceHTTPError):
        web.shorten("https://example.com", service="goo.gl")

    mock_requests.replace(
        mock_requests.POST,
        "https://www.googleapis.com/urlshortener/v1/url",
        json={"id": "https://goo.gl/foobar"},
    )
    assert (
        web.shorten("https://example.com", service="goo.gl")
        == "https://goo.gl/foobar"
    )

    with pytest.raises(web.ServiceError):
        web.shorten("https://example.com", service="git.io")

    mock_requests.add(
        mock_requests.POST,
        "http://git.io",
        status=400,
    )
    with pytest.raises(web.ServiceHTTPError):
        web.shorten("https://example.com", service="git.io")

    mock_requests.replace(mock_requests.POST, "http://git.io", body="error")
    with pytest.raises(web.ServiceHTTPError):
        web.shorten("https://example.com", service="git.io")

    mock_requests.replace(mock_requests.POST, "http://git.io", body="error")
    with pytest.raises(web.ServiceHTTPError):
        web.shorten("https://example.com", service="git.io")

    mock_requests.replace(
        mock_requests.POST,
        "http://git.io",
        headers={"Location": "http://git.io/foobar123"},
        status=requests.codes.created,
    )
    assert (
        web.shorten("https://example.com", service="git.io")
        == "http://git.io/foobar123"
    )

    with pytest.raises(web.ServiceHTTPError):
        web.shorten("https://example.com", service="git.io", custom="test")


def test_isgd_errors(mock_requests):
    mock_requests.add(mock_requests.GET, "http://is.gd/create.php", status=429)
    from cloudbot.util import web

    with pytest.raises(web.ServiceHTTPError):
        web.shorten("https://example.com", service="is.gd")

    mock_requests.reset()
    with pytest.raises(web.ServiceError):
        web.shorten("https://example.com", service="is.gd")


def test_try_shorten(mock_requests):
    mock_requests.add(
        mock_requests.GET,
        "http://is.gd/create.php",
        json={"shorturl": "https://is.gd/foobar"},
    )
    from cloudbot.util import web

    assert (
        web.try_shorten("https://example.com", service="is.gd")
        == "https://is.gd/foobar"
    )

    mock_requests.replace(
        mock_requests.GET,
        "http://is.gd/create.php",
        json={"errormessage": "Error occurred"},
    )
    assert (
        web.try_shorten("https://example.com", service="is.gd")
        == "https://example.com"
    )


def test_expand(mock_requests):
    mock_requests.add(
        mock_requests.GET,
        "http://is.gd/forward.php?shorturl=https%3A%2F%2Fis.gd%2Ffoobar&format=json",
        json={"url": "https://example.com"},
    )
    from cloudbot.util import web

    assert (
        web.expand("https://is.gd/foobar", service="is.gd")
        == "https://example.com"
    )
    assert web.expand("https://is.gd/foobar") == "https://example.com"

    mock_requests.replace(
        mock_requests.GET,
        "http://is.gd/forward.php?shorturl=https%3A%2F%2Fis.gd%2Ffoobar&format=json",
        status=404,
    )

    with pytest.raises(web.ServiceHTTPError):
        web.expand("https://is.gd/foobar")

    mock_requests.replace(
        mock_requests.GET,
        "http://is.gd/forward.php?shorturl=https%3A%2F%2Fis.gd%2Ffoobar&format=json",
        json={"errormessage": "Error"},
    )

    with pytest.raises(web.ServiceHTTPError):
        web.expand("https://is.gd/foobar")

    mock_requests.reset()

    with pytest.raises(web.ServiceError):
        web.expand("https://is.gd/foobar")

    with pytest.raises(web.ServiceError):
        web.expand("http://my.shortener/foobar")

    mock_requests.add(
        mock_requests.GET,
        "http://my.shortener/foobar",
        headers={"Location": "https://example.com"},
    )
    assert web.expand("http://my.shortener/foobar") == "https://example.com"

    mock_requests.replace(
        mock_requests.GET, "http://my.shortener/foobar", status=404
    )
    with pytest.raises(web.ServiceHTTPError):
        web.expand("http://my.shortener/foobar")

    mock_requests.replace(mock_requests.GET, "http://my.shortener/foobar")
    with pytest.raises(web.ServiceHTTPError):
        web.expand("http://my.shortener/foobar")

    with pytest.raises(web.ServiceError):
        web.expand("http://goo.gl/foobar")

    mock_requests.add(
        mock_requests.GET,
        "https://www.googleapis.com/urlshortener/v1/url",
        status=404,
    )

    with pytest.raises(web.ServiceHTTPError):
        web.expand("http://goo.gl/foobar")

    mock_requests.replace(
        mock_requests.GET,
        "https://www.googleapis.com/urlshortener/v1/url",
        json={"error": {"message": "Error"}},
    )

    with pytest.raises(web.ServiceHTTPError):
        web.expand("http://goo.gl/foobar")

    mock_requests.replace(
        mock_requests.GET,
        "https://www.googleapis.com/urlshortener/v1/url",
        json={"longUrl": "https://example.com"},
    )

    assert web.expand("http://goo.gl/foobar") == "https://example.com"


def test_register_duplicate_paste():
    from cloudbot.util import web

    obj = object()
    obj1 = object()

    web.pastebins.register("test", obj)
    with pytest.raises(ValueError):
        web.pastebins.register("test", obj1)

    importlib.reload(web)


def test_remove_paste():
    from cloudbot.util import web

    obj = object()

    web.pastebins.register("test", obj)
    assert web.pastebins.get("test") is obj
    web.pastebins.remove("test")
    assert web.pastebins.get("test") is None

    importlib.reload(web)
