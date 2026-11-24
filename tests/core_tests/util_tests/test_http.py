from unittest.mock import call, patch

from cloudbot.util import http


def test_open_request() -> None:
    with (
        patch("urllib.request.Request") as mocked,
        patch("urllib.request.build_opener") as mocked_open_build,
    ):
        http.open_request("https://host.invalid")
        assert mocked.mock_calls == [
            call("https://host.invalid", None, method=None),
            call().add_header(
                "User-Agent", "Cloudbot/DEV http://github.com/CloudDev/CloudBot"
            ),
        ]
        assert mocked_open_build.mock_calls == [call(), call().open(mocked())]


def test_open_request_with_cookies() -> None:
    with (
        patch("urllib.request.Request") as mocked,
        patch("urllib.request.build_opener") as mocked_open_build,
        patch("urllib.request.HTTPCookieProcessor") as mocked_cookie_proc,
    ):
        http.open_request(
            "https://host.invalid", cookies=True, referer="https://example.com"
        )
        assert mocked.mock_calls == [
            call("https://host.invalid", None, method=None),
            call().add_header(
                "User-Agent", "Cloudbot/DEV http://github.com/CloudDev/CloudBot"
            ),
            call().add_header("Referer", "https://example.com"),
        ]
        assert mocked_open_build.mock_calls == [
            call(mocked_cookie_proc(http.jar)),
            call(mocked_cookie_proc(http.jar)).open(mocked()),
        ]


def test_get_soup() -> None:
    test_data = """
    <html>
        <body>
            <div class="thing"><p>foobar</p></div>
        </body>
    </html>
    """
    with patch("cloudbot.util.http.get", lambda *a, **k: test_data):  # noqa: ARG005
        soup = http.get_soup("http://example.com")
        tag = soup.find("div", {"class": "thing"})
        assert tag is not None
        subtag = tag.p
        assert subtag is not None
        assert subtag.text == "foobar"
