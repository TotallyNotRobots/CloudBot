from plugins import github
from tests.util.mock_bot import MockBot


def test_shortcuts(patch_try_shorten, mock_requests):
    mock_requests.add(
        "GET",
        "https://api.github.com/repos/TotallyNotRobots/CloudBot/issues",
        json=[
            {
                "html_url": "html_url",
                "number": 1,
                "title": "issue title",
                "body": "body",
                "state": "open",
                "user": {"login": "foobar"},
            }
        ],
    )
    bot = MockBot({})
    github.load_shortcuts(bot)
    assert github.issue_cmd("cloudbot") == "Repository has 1 open issues."


def test_no_issues(patch_try_shorten, mock_requests):
    mock_requests.add(
        "GET",
        "https://api.github.com/repos/TotallyNotRobots/CloudBot/issues",
        json=[],
    )
    expected = "Repository has no open issues."
    assert github.issue_cmd("TotallyNotRobots/CloudBot") == expected


def test_issue_count(patch_try_shorten, mock_requests):
    mock_requests.add(
        "GET",
        "https://api.github.com/repos/TotallyNotRobots/CloudBot/issues",
        json=[{}],
    )
    expected = "Repository has 1 open issues."
    assert github.issue_cmd("TotallyNotRobots/CloudBot") == expected


def test_issue_info(patch_try_shorten, mock_requests):
    mock_requests.add(
        "GET",
        "https://api.github.com/repos/TotallyNotRobots/CloudBot/issues/1",
        json={
            "html_url": "html_url",
            "number": 1,
            "title": "issue title",
            "body": "body",
            "state": "open",
            "user": {"login": "foobar"},
        },
    )
    expected = (
        "Issue #1 (\x033\x02Opened\x02\x0f by foobar): html_url | "
        "issue title: body"
    )
    assert github.issue_cmd("TotallyNotRobots/CloudBot 1") == expected


def test_issue_info_closed(patch_try_shorten, mock_requests):
    mock_requests.add(
        "GET",
        "https://api.github.com/repos/TotallyNotRobots/CloudBot/issues/1",
        json={
            "html_url": "html_url",
            "number": 1,
            "title": "issue title",
            "body": "body",
            "state": "closed",
            "user": {"login": "foobar"},
            "closed_by": {"login": "baz"},
        },
    )
    expected = (
        "Issue #1 (\x034\x02Closed\x02\x0f by baz): html_url | issue "
        "title: body"
    )
    assert github.issue_cmd("TotallyNotRobots/CloudBot 1") == expected
