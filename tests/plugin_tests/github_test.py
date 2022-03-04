from unittest.mock import MagicMock, call

import pytest
from requests import HTTPError

from plugins import github


def test_github(mock_requests, mock_bot, patch_try_shorten):
    owner = "foo"
    repo = "bar"
    num = 123
    mock_requests.add(
        "GET",
        f"https://api.github.com/repos/{owner}/{repo}/issues/{num}",
        json={
            "html_url": "https://foo.bar.example",
            "number": num,
            "title": "This is a test",
            "body": "Test issue",
            "state": "open",
            "user": {"login": "linuxdaemon"},
        },
    )

    github.load_shortcuts(mock_bot)
    event = MagicMock()
    res = github.issue_cmd(f"{owner}/{repo} {num}", event)
    expected = "Issue #123 (\x033\x02Opened\x02\x0f by linuxdaemon): https://foo.bar.example | This is a test: Test issue"
    assert res == expected
    assert event.mock_calls == []


def test_github_error(mock_requests, mock_bot, patch_try_shorten):
    owner = "foo"
    repo = "bar"
    num = 123
    mock_requests.add(
        "GET",
        f"https://api.github.com/repos/{owner}/{repo}/issues/{num}",
        json={},
        status=403,
    )

    github.load_shortcuts(mock_bot)
    event = MagicMock()
    with pytest.raises(HTTPError):
        github.issue_cmd(f"{owner}/{repo} {num}", event)

    assert event.mock_calls == [
        call.reply(
            "403 Client Error: Forbidden for url: https://api.github.com/repos/foo/bar/issues/123"
        )
    ]


def test_github_closed(mock_requests, mock_bot, patch_try_shorten):
    owner = "foo"
    repo = "bar"
    num = 123
    github.shortcuts[repo] = (owner, repo)
    mock_requests.add(
        "GET",
        f"https://api.github.com/repos/{owner}/{repo}/issues/{num}",
        json={
            "html_url": "https://foo.bar.example",
            "number": num,
            "title": "This is a test",
            "body": "Test issue",
            "state": "closed",
            "closed_by": {"login": "A_D"},
            "user": {"login": "linuxdaemon"},
        },
    )

    github.load_shortcuts(mock_bot)
    event = MagicMock()
    res = github.issue_cmd(f"{repo} {num}", event)
    expected = "Issue #123 (\x034\x02Closed\x02\x0f by A_D): https://foo.bar.example | This is a test: Test issue"
    assert res == expected
    assert event.mock_calls == []


def test_github_shortcut(mock_requests, mock_bot, patch_try_shorten):
    owner = "foo"
    repo = "bar"
    num = 123
    github.shortcuts[repo] = (owner, repo)
    mock_requests.add(
        "GET",
        f"https://api.github.com/repos/{owner}/{repo}/issues/{num}",
        json={
            "html_url": "https://foo.bar.example",
            "number": num,
            "title": "This is a test",
            "body": "Test issue",
            "state": "open",
            "user": {"login": "linuxdaemon"},
        },
    )

    github.load_shortcuts(mock_bot)
    event = MagicMock()
    res = github.issue_cmd(f"{repo} {num}", event)
    expected = "Issue #123 (\x033\x02Opened\x02\x0f by linuxdaemon): https://foo.bar.example | This is a test: Test issue"
    assert res == expected
    assert event.mock_calls == []


def test_github_no_num_no_issues(mock_requests, mock_bot, patch_try_shorten):
    owner = "foo"
    repo = "bar"
    mock_requests.add(
        "GET", f"https://api.github.com/repos/{owner}/{repo}/issues", json=[]
    )

    github.load_shortcuts(mock_bot)
    event = MagicMock()
    res = github.issue_cmd(f"{owner}/{repo}", event)
    expected = "Repository has no open issues."
    assert res == expected
    assert event.mock_calls == []


def test_github_no_num(mock_requests, mock_bot, patch_try_shorten):
    owner = "foo"
    repo = "bar"
    mock_requests.add(
        "GET", f"https://api.github.com/repos/{owner}/{repo}/issues", json=[{}]
    )

    github.load_shortcuts(mock_bot)
    event = MagicMock()
    res = github.issue_cmd(f"{owner}/{repo}", event)
    expected = "Repository has 1 open issues."
    assert res == expected
    assert event.mock_calls == []


def test_github_no_exist(mock_requests, mock_bot, patch_try_shorten):
    owner = "foo"
    repo = "bar"
    num = 123
    mock_requests.add(
        "GET",
        f"https://api.github.com/repos/{owner}/{repo}/issues/{num}",
        json={},
        status=404,
    )

    github.load_shortcuts(mock_bot)
    event = MagicMock()
    res = github.issue_cmd(f"{owner}/{repo} {num}", event)
    expected = "Issue #123 doesn't exist in foo/bar"
    assert res == expected
    assert event.mock_calls == []
