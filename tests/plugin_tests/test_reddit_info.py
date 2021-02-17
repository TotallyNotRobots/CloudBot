from unittest.mock import MagicMock

import pytest


@pytest.mark.parametrize(
    "text,post_id",
    [
        ("http://reddit.com/r/foo/comments/bar", "bar"),
        ("http://www.reddit.com/r/foo/comments/bar", "bar"),
        ("http://np.reddit.com/r/foo/comments/bar", "bar"),
        ("np.reddit.com/r/foo/comments/bar", "bar"),
        ("reddit.com/r/foo/comments/bar", "bar"),
        (
            "some random text: http://reddit.com/r/foo/comments/bar and more text",
            "bar",
        ),
    ],
)
def test_post_re_match(text, post_id):
    from plugins.reddit_info import post_re

    match = post_re.search(text)
    assert match and (match.group(1) == post_id)


@pytest.mark.parametrize(
    "text",
    [
        "https://reddit.com/r/foo",
        "http://fakereddit.com/r/foo/comments/bar",
        " fakereddit.com/r/foo/comments/bar",
        "fakereddit.com/r/foo/comments/bar",
    ],
)
def test_post_re_no_match(text):
    from plugins.reddit_info import post_re

    assert not post_re.search(text)


@pytest.mark.parametrize(
    "text,output",
    [
        ("test", "test"),
        ("/test", "test"),
        ("test/", "test"),
        ("/test/", "test"),
        ("r/test", "test"),
        ("r/test/", "test"),
        ("/r/test", "test"),
        ("/r/test/", "test"),
    ],
)
def test_get_user(text, output):
    from plugins.reddit_info import get_sub

    assert get_sub(text) == output


@pytest.mark.parametrize(
    "text,output",
    [
        ("test", "test"),
        ("test/", "test"),
        ("/test", "test"),
        ("/test/", "test"),
        ("/u/test", "test"),
        ("u/test", "test"),
        ("/user/test", "test"),
        ("user/test", "test"),
        ("/u/test/", "test"),
        ("u/test/", "test"),
        ("/user/test/", "test"),
        ("user/test/", "test"),
        ("user", "user"),
        ("/user", "user"),
        ("user/", "user"),
        ("/user/", "user"),
        ("u/user", "user"),
        ("/u/user", "user"),
    ],
)
def test_get_sub(text, output):
    from plugins.reddit_info import get_user

    assert get_user(text) == output


def test_reddit_no_posts(mock_requests):
    from plugins import reddit_info

    mock_requests.add(
        "GET",
        "https://reddit.com/r/foobar/.json",
        json={"data": {"children": []}},
    )

    reply_mock = MagicMock()

    response = reddit_info.reddit("/r/FooBar", reply_mock)

    assert response == "There do not appear to be any posts to show."
