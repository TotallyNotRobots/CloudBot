from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from requests import HTTPError

from cloudbot.event import CommandEvent, Event
from plugins import reddit_info
from tests.util import HookResult, wrap_hook_response

if TYPE_CHECKING:
    from responses import RequestsMock


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
def test_post_re_match(text, post_id) -> None:
    match = reddit_info.post_re.search(text)
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
def test_post_re_no_match(text) -> None:
    assert not reddit_info.post_re.search(text)


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
def test_get_sub(text, output) -> None:
    assert reddit_info.get_sub(text) == output


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
def test_get_user(text, output) -> None:
    assert reddit_info.get_user(text) == output


def test_reddit_no_posts(mock_requests) -> None:
    mock_requests.add(
        "GET",
        "https://reddit.com/r/foobar/.json",
        json={"data": {"children": []}},
    )

    reply_mock = MagicMock()

    response = reddit_info.reddit("/r/FooBar", reply_mock)

    assert response == "There do not appear to be any posts to show."


def test_reddit_random_post(mock_requests) -> None:
    mock_requests.add(
        "GET",
        "https://reddit.com/r/foobar/.json",
        json={
            "kind": "Listing",
            "data": {
                "after": None,
                "dist": 10,
                "modhash": "2oy8frlekob157d6466f71eded97c0cbb8b3c35a176ddf4c6b",
                "geo_filter": None,
                "children": [
                    {
                        "kind": "t3",
                        "data": {
                            "approved_at_utc": None,
                            "subreddit": "foobar",
                            "selftext": "Can someone please give me invitation for Google foobar???",
                            "author_fullname": "t2_eh4h4hy8",
                            "saved": False,
                            "mod_reason_title": None,
                            "gilded": 0,
                            "clicked": False,
                            "title": "Need foobar",
                            "link_flair_richtext": [],
                            "subreddit_name_prefixed": "r/foobar",
                            "hidden": False,
                            "pwls": None,
                            "link_flair_css_class": None,
                            "downs": 0,
                            "thumbnail_height": None,
                            "top_awarded_type": None,
                            "hide_score": False,
                            "name": "t3_pmmq8h",
                            "quarantine": False,
                            "link_flair_text_color": "dark",
                            "upvote_ratio": 1.0,
                            "author_flair_background_color": None,
                            "subreddit_type": "restricted",
                            "ups": 1,
                            "total_awards_received": 0,
                            "media_embed": {},
                            "thumbnail_width": None,
                            "author_flair_template_id": None,
                            "is_original_content": False,
                            "user_reports": [],
                            "secure_media": None,
                            "is_reddit_media_domain": False,
                            "is_meta": False,
                            "category": None,
                            "secure_media_embed": {},
                            "link_flair_text": None,
                            "can_mod_post": False,
                            "score": 1,
                            "approved_by": None,
                            "is_created_from_ads_ui": False,
                            "author_premium": False,
                            "thumbnail": "self",
                            "edited": False,
                            "author_flair_css_class": None,
                            "author_flair_richtext": [],
                            "gildings": {},
                            "content_categories": None,
                            "is_self": True,
                            "mod_note": None,
                            "created": 1631424037.0,
                            "link_flair_type": "text",
                            "wls": None,
                            "removed_by_category": None,
                            "banned_by": None,
                            "author_flair_type": "text",
                            "domain": "self.foobar",
                            "allow_live_comments": False,
                            "selftext_html": '&lt;!-- SC_OFF --&gt;&lt;div class="md"&gt;&lt;p&gt;Can someone please give me invitation for Google foobar???&lt;/p&gt;\n&lt;/div&gt;&lt;!-- SC_ON --&gt;',
                            "likes": None,
                            "suggested_sort": None,
                            "banned_at_utc": None,
                            "view_count": None,
                            "archived": False,
                            "no_follow": True,
                            "is_crosspostable": True,
                            "pinned": False,
                            "over_18": True,
                            "all_awardings": [],
                            "awarders": [],
                            "media_only": False,
                            "can_gild": False,
                            "spoiler": False,
                            "locked": False,
                            "author_flair_text": None,
                            "treatment_tags": [],
                            "visited": False,
                            "removed_by": None,
                            "num_reports": None,
                            "distinguished": None,
                            "subreddit_id": "t5_2qhdc",
                            "author_is_blocked": False,
                            "mod_reason_by": None,
                            "removal_reason": None,
                            "link_flair_background_color": "",
                            "id": "pmmq8h",
                            "is_robot_indexable": True,
                            "report_reasons": None,
                            "author": "HEROFIGHTERy",
                            "discussion_type": None,
                            "num_comments": 3,
                            "send_replies": True,
                            "contest_mode": False,
                            "mod_reports": [],
                            "author_patreon_flair": False,
                            "author_flair_text_color": None,
                            "permalink": "/r/foobar/comments/pmmq8h/need_foobar/",
                            "stickied": False,
                            "url": "https://www.reddit.com/r/foobar/comments/pmmq8h/need_foobar/",
                            "subreddit_subscribers": 66,
                            "created_utc": 1631424037.0,
                            "num_crossposts": 0,
                            "media": None,
                            "is_video": False,
                        },
                    },
                ],
                "before": None,
            },
        },
    )

    conn = MagicMock()
    event = CommandEvent(
        base_event=Event(
            conn=conn,
            bot=conn.bot,
        ),
        text="/r/foobar",
        triggered_command="reddit",
        cmd_prefix=".",
        hook=MagicMock(),
    )

    assert wrap_hook_response(reddit_info.reddit, event) == [
        (
            "return",
            "\x02Need foobar : foobar\x02 - 3 comments, 1 point - \x02HEROFIGHTERy\x02 4y ago - https://redd.it/pmmq8h \x02\x0304NSFW\x0f",
        ),
    ]


def test_reddit_random_post_sub_not_found(mock_requests: RequestsMock) -> None:
    mock_requests.add(
        "GET",
        "https://reddit.com/r/foobar/.json",
        status=404,
    )

    conn = MagicMock()
    event = CommandEvent(
        base_event=Event(
            conn=conn,
            bot=conn.bot,
            channel="#foo",
            nick="foo",
        ),
        text="/r/foobar",
        triggered_command="reddit",
        cmd_prefix=".",
        hook=MagicMock(),
    )

    responses = list[HookResult]()
    with pytest.raises(HTTPError):
        wrap_hook_response(reddit_info.reddit, event, responses)

    assert responses == [
        (
            "message",
            (
                "#foo",
                "(foo) Error: 404 Client Error: Not Found for url: https://reddit.com/r/foobar/.json",
            ),
        ),
    ]


def test_karma(mock_requests, freeze_time) -> None:
    mock_requests.add(
        "GET",
        "https://reddit.com/user/foo/about.json",
        json={
            "kind": "t2",
            "data": {
                "is_employee": False,
                "is_friend": False,
                "subreddit": {
                    "default_set": True,
                    "user_is_contributor": False,
                    "banner_img": "",
                    "allowed_media_in_comments": [],
                    "user_is_banned": False,
                    "free_form_reports": True,
                    "community_icon": None,
                    "show_media": True,
                    "icon_color": "#FFB470",
                    "user_is_muted": None,
                    "display_name": "u_foo",
                    "header_img": None,
                    "title": "",
                    "previous_names": [],
                    "over_18": False,
                    "icon_size": [256, 256],
                    "primary_color": "",
                    "icon_img": "https://www.redditstatic.com/avatars/defaults/v2/avatar_default_1.png",
                    "description": "",
                    "submit_link_label": "",
                    "header_size": None,
                    "restrict_posting": True,
                    "restrict_commenting": False,
                    "subscribers": 0,
                    "submit_text_label": "",
                    "is_default_icon": True,
                    "link_flair_position": "",
                    "display_name_prefixed": "u/foo",
                    "key_color": "",
                    "name": "t5_21ni2g",
                    "is_default_banner": True,
                    "url": "/user/foo/",
                    "quarantine": False,
                    "banner_size": None,
                    "user_is_moderator": False,
                    "accept_followers": True,
                    "public_description": "",
                    "link_flair_enabled": False,
                    "disable_contributor_requests": False,
                    "subreddit_type": "user",
                    "user_is_subscriber": False,
                },
                "snoovatar_size": None,
                "awardee_karma": 0,
                "id": "1tz5",
                "verified": True,
                "is_gold": False,
                "is_mod": False,
                "awarder_karma": 0,
                "has_verified_email": True,
                "icon_img": "https://www.redditstatic.com/avatars/defaults/v2/avatar_default_1.png",
                "hide_from_robots": False,
                "link_karma": 8,
                "pref_show_snoovatar": False,
                "is_blocked": False,
                "total_karma": 72,
                "accept_chats": True,
                "name": "foo",
                "created": 1122350400.0,
                "created_utc": 1122350400.0,
                "snoovatar_img": "",
                "comment_karma": 64,
                "accept_followers": True,
                "has_subscribed": True,
                "accept_pms": True,
            },
        },
    )

    conn = MagicMock()
    event = CommandEvent(
        base_event=Event(
            conn=conn,
            bot=conn.bot,
        ),
        text="foo",
        triggered_command="ruser",
        cmd_prefix=".",
        hook=MagicMock(),
    )

    assert wrap_hook_response(reddit_info.karma, event) == [
        (
            "return",
            "\x02foo\x02 \x028\x02 link karma and \x0264\x02 comment karma | email has been verified | cake day is July 25 | redditor for 14 years.",
        ),
    ]


def test_cake_day(mock_requests, freeze_time) -> None:
    mock_requests.add(
        "GET",
        "https://reddit.com/user/foo/about.json",
        json={
            "kind": "t2",
            "data": {
                "is_employee": False,
                "is_friend": False,
                "subreddit": {
                    "default_set": True,
                    "user_is_contributor": False,
                    "banner_img": "",
                    "allowed_media_in_comments": [],
                    "user_is_banned": False,
                    "free_form_reports": True,
                    "community_icon": None,
                    "show_media": True,
                    "icon_color": "#FFB470",
                    "user_is_muted": None,
                    "display_name": "u_foo",
                    "header_img": None,
                    "title": "",
                    "previous_names": [],
                    "over_18": False,
                    "icon_size": [256, 256],
                    "primary_color": "",
                    "icon_img": "https://www.redditstatic.com/avatars/defaults/v2/avatar_default_1.png",
                    "description": "",
                    "submit_link_label": "",
                    "header_size": None,
                    "restrict_posting": True,
                    "restrict_commenting": False,
                    "subscribers": 0,
                    "submit_text_label": "",
                    "is_default_icon": True,
                    "link_flair_position": "",
                    "display_name_prefixed": "u/foo",
                    "key_color": "",
                    "name": "t5_21ni2g",
                    "is_default_banner": True,
                    "url": "/user/foo/",
                    "quarantine": False,
                    "banner_size": None,
                    "user_is_moderator": False,
                    "accept_followers": True,
                    "public_description": "",
                    "link_flair_enabled": False,
                    "disable_contributor_requests": False,
                    "subreddit_type": "user",
                    "user_is_subscriber": False,
                },
                "snoovatar_size": None,
                "awardee_karma": 0,
                "id": "1tz5",
                "verified": True,
                "is_gold": False,
                "is_mod": False,
                "awarder_karma": 0,
                "has_verified_email": True,
                "icon_img": "https://www.redditstatic.com/avatars/defaults/v2/avatar_default_1.png",
                "hide_from_robots": False,
                "link_karma": 8,
                "pref_show_snoovatar": False,
                "is_blocked": False,
                "total_karma": 72,
                "accept_chats": True,
                "name": "foo",
                "created": 1122350400.0,
                "created_utc": 1122350400.0,
                "snoovatar_img": "",
                "comment_karma": 64,
                "accept_followers": True,
                "has_subscribed": True,
                "accept_pms": True,
            },
        },
    )

    conn = MagicMock()
    event = CommandEvent(
        base_event=Event(
            conn=conn,
            bot=conn.bot,
        ),
        text="foo",
        triggered_command="cakeday",
        cmd_prefix=".",
        hook=MagicMock(),
    )

    assert wrap_hook_response(reddit_info.cake_day, event) == [
        (
            "return",
            "\x02foo's\x02 cake day is July 25, they have been a redditor for 14 years.",
        ),
    ]
