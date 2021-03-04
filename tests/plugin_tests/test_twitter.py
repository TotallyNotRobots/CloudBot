from unittest.mock import MagicMock

import pytest
import tweepy

from plugins import twitter
from tests.util.mock_config import MockConfig


@pytest.fixture()
def mock_conn():
    bot = MagicMock()

    mock_conn = MagicMock()
    mock_conn.config = {}
    mock_conn.bot = bot
    bot.config = MockConfig(bot)
    bot.config.update(
        {
            "api_keys": {
                "twitter_consumer_key": "foo",
                "twitter_consumer_secret": "bar",
                "twitter_access_token": "baz",
                "twitter_access_secret": "fizz",
            }
        }
    )
    yield mock_conn


def test_twitter_cmd_id(mock_requests, mock_conn, freeze_time):
    bot = mock_conn.bot

    twitter.set_api(bot)
    event = MagicMock()
    event.conn = mock_conn
    event.bot = bot
    tweet_id = 1050118621198921728
    event.text = f"{tweet_id}"
    user_name = "TwitterAPI"
    user_display = "Twitter API"
    tweet_text = "To make room for more expression, we will now count all emojis as equal—including those with gender and skin t… https://t.co/MkGjXf9aXm"
    response = {
        "created_at": "Wed Oct 10 20:19:24 +0000 2018",
        "id": tweet_id,
        "id_str": "1050118621198921728",
        "text": tweet_text,
        "truncated": True,
        "entities": {
            "hashtags": [],
            "symbols": [],
            "user_mentions": [],
            "urls": [
                {
                    "url": "https://t.co/MkGjXf9aXm",
                    "expanded_url": "https://twitter.com/i/web/status/1050118621198921728",
                    "display_url": "twitter.com/i/web/status/1…",
                    "indices": [117, 140],
                }
            ],
        },
        "source": '<a href="http://twitter.com" rel="nofollow">Twitter Web Client</a>',
        "in_reply_to_status_id": None,
        "in_reply_to_status_id_str": None,
        "in_reply_to_user_id": None,
        "in_reply_to_user_id_str": None,
        "in_reply_to_screen_name": None,
        "user": {
            "id": 6253282,
            "id_str": "6253282",
            "name": user_display,
            "screen_name": user_name,
            "location": "San Francisco, CA",
            "description": "The Real Twitter API. Tweets about API changes, service issues and our Developer Platform. Don't get an answer? It's on my website.",
            "url": "https://t.co/8IkCzCDr19",
            "entities": {
                "url": {
                    "urls": [
                        {
                            "url": "https://t.co/8IkCzCDr19",
                            "expanded_url": "https://developer.twitter.com",
                            "display_url": "developer.twitter.com",
                            "indices": [0, 23],
                        }
                    ]
                },
                "description": {"urls": []},
            },
            "protected": False,
            "followers_count": 6128663,
            "friends_count": 12,
            "listed_count": 12900,
            "created_at": "Wed May 23 06:01:13 +0000 2007",
            "favourites_count": 32,
            "utc_offset": None,
            "time_zone": None,
            "geo_enabled": None,
            "verified": True,
            "statuses_count": 3659,
            "lang": "null",
            "contributors_enabled": None,
            "is_translator": None,
            "is_translation_enabled": None,
            "profile_background_color": "null",
            "profile_background_image_url": "null",
            "profile_background_image_url_https": "null",
            "profile_background_tile": None,
            "profile_image_url": "null",
            "profile_image_url_https": "https://pbs.twimg.com/profile_images/942858479592554497/BbazLO9L_normal.jpg",
            "profile_banner_url": "https://pbs.twimg.com/profile_banners/6253282/1497491515",
            "profile_link_color": "null",
            "profile_sidebar_border_color": "null",
            "profile_sidebar_fill_color": "null",
            "profile_text_color": "null",
            "profile_use_background_image": None,
            "has_extended_profile": None,
            "default_profile": False,
            "default_profile_image": False,
            "following": None,
            "follow_request_sent": None,
            "notifications": None,
            "translator_type": "null",
        },
        "geo": None,
        "coordinates": None,
        "place": None,
        "contributors": None,
        "is_quote_status": False,
        "retweet_count": 161,
        "favorite_count": 296,
        "favorited": False,
        "retweeted": False,
        "possibly_sensitive": False,
        "possibly_sensitive_appealable": False,
        "lang": "en",
    }

    mock_requests.add(
        "GET",
        f"https://api.twitter.com/1.1/statuses/show.json?id={tweet_id}&tweet_mode=extended",
        json=response,
    )

    res = twitter.twitter(event.text, event.reply, event.conn)

    time_ago = "10 months and 15 days ago"
    expected = f"✓@\2{user_name}\2 ({user_display}): {tweet_text} ({time_ago})"
    assert res == expected
    assert event.mock_calls == []


def test_twitter_cmd_name(mock_requests, mock_conn, freeze_time):
    bot = mock_conn.bot

    twitter.set_api(bot)
    event = MagicMock()
    event.conn = mock_conn
    event.bot = bot
    user_name = "TwitterAPI"
    event.text = user_name
    response = {
        "id": 6253282,
        "id_str": "6253282",
        "name": "Twitter API",
        "screen_name": "TwitterAPI",
        "location": "San Francisco, CA",
        "profile_location": None,
        "description": "The Real Twitter API. Tweets about API changes, service issues and our Developer Platform. Don't get an answer? It's on my website.",
        "url": "https://t.co/8IkCzCDr19",
        "entities": {
            "url": {
                "urls": [
                    {
                        "url": "https://t.co/8IkCzCDr19",
                        "expanded_url": "https://developer.twitter.com",
                        "display_url": "developer.twitter.com",
                        "indices": [0, 23],
                    }
                ]
            },
            "description": {"urls": []},
        },
        "protected": False,
        "followers_count": 6133636,
        "friends_count": 12,
        "listed_count": 12936,
        "created_at": "Wed May 23 06:01:13 +0000 2007",
        "favourites_count": 31,
        "utc_offset": None,
        "time_zone": None,
        "geo_enabled": None,
        "verified": True,
        "statuses_count": 3656,
        "lang": None,
        "contributors_enabled": None,
        "is_translator": None,
        "is_translation_enabled": None,
        "profile_background_color": None,
        "profile_background_image_url": None,
        "profile_background_image_url_https": None,
        "profile_background_tile": None,
        "profile_image_url": None,
        "profile_image_url_https": "https://pbs.twimg.com/profile_images/942858479592554497/BbazLO9L_normal.jpg",
        "profile_banner_url": None,
        "profile_link_color": None,
        "profile_sidebar_border_color": None,
        "profile_sidebar_fill_color": None,
        "profile_text_color": None,
        "profile_use_background_image": None,
        "has_extended_profile": None,
        "default_profile": False,
        "default_profile_image": False,
        "following": None,
        "follow_request_sent": None,
        "notifications": None,
        "translator_type": None,
    }

    mock_requests.add(
        "GET",
        f"https://api.twitter.com/1.1/users/show.json?id={user_name}&tweet_mode=extended",
        json=response,
    )

    mock_requests.add(
        "GET",
        "https://api.twitter.com/1.1/statuses/user_timeline.json?id=6253282&count=1&tweet_mode=extended",
        json=[
            {
                "created_at": "Thu Apr 06 15:28:43 +0000 2017",
                "id": 850007368138018817,
                "id_str": "850007368138018817",
                "text": "RT @TwitterDev: 1/ Today we’re sharing our vision for the future of the Twitter API platform!nhttps://t.co/XweGngmxlP",
                "truncated": False,
                "entities": {
                    "hashtags": [],
                    "symbols": [],
                    "user_mentions": [
                        {
                            "screen_name": "TwitterDev",
                            "name": "TwitterDev",
                            "id": 2244994945,
                            "id_str": "2244994945",
                            "indices": [3, 14],
                        }
                    ],
                    "urls": [
                        {
                            "url": "https://t.co/XweGngmxlP",
                            "expanded_url": "https://cards.twitter.com/cards/18ce53wgo4h/3xo1c",
                            "display_url": "cards.twitter.com/cards/18ce53wg…",
                            "indices": [94, 117],
                        }
                    ],
                },
                "source": '<a href="http://twitter.com" rel="nofollow">Twitter Web Client</a>',
                "in_reply_to_status_id": None,
                "in_reply_to_status_id_str": None,
                "in_reply_to_user_id": None,
                "in_reply_to_user_id_str": None,
                "in_reply_to_screen_name": None,
                "user": {
                    "id": 6253282,
                    "id_str": "6253282",
                    "name": "Twitter API",
                    "screen_name": "twitterapi",
                    "location": "San Francisco, CA",
                    "description": "The Real Twitter API. I tweet about API changes, service issues and happily answer questions about Twitter and our API. Don't get an answer? It's on my website.",
                    "url": "http://t.co/78pYTvWfJd",
                    "entities": {
                        "url": {
                            "urls": [
                                {
                                    "url": "http://t.co/78pYTvWfJd",
                                    "expanded_url": "https://dev.twitter.com",
                                    "display_url": "dev.twitter.com",
                                    "indices": [0, 22],
                                }
                            ]
                        },
                        "description": {"urls": []},
                    },
                    "protected": False,
                    "followers_count": 6172353,
                    "friends_count": 46,
                    "listed_count": 13091,
                    "created_at": "Wed May 23 06:01:13 +0000 2007",
                    "favourites_count": 26,
                    "utc_offset": -25200,
                    "time_zone": "Pacific Time (US & Canada)",
                    "geo_enabled": True,
                    "verified": True,
                    "statuses_count": 3583,
                    "lang": "en",
                    "contributors_enabled": False,
                    "is_translator": False,
                    "is_translation_enabled": False,
                    "profile_background_color": "C0DEED",
                    "profile_background_image_url": "http://pbs.twimg.com/profile_background_images/656927849/miyt9dpjz77sc0w3d4vj.png",
                    "profile_background_image_url_https": "https://pbs.twimg.com/profile_background_images/656927849/miyt9dpjz77sc0w3d4vj.png",
                    "profile_background_tile": True,
                    "profile_image_url": "http://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3_normal.png",
                    "profile_image_url_https": "https://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3_normal.png",
                    "profile_banner_url": "https://pbs.twimg.com/profile_banners/6253282/1431474710",
                    "profile_link_color": "0084B4",
                    "profile_sidebar_border_color": "C0DEED",
                    "profile_sidebar_fill_color": "DDEEF6",
                    "profile_text_color": "333333",
                    "profile_use_background_image": True,
                    "has_extended_profile": False,
                    "default_profile": False,
                    "default_profile_image": False,
                    "following": True,
                    "follow_request_sent": False,
                    "notifications": False,
                    "translator_type": "regular",
                },
                "geo": None,
                "coordinates": None,
                "place": None,
                "contributors": None,
                "retweeted_status": {
                    "created_at": "Thu Apr 06 15:24:15 +0000 2017",
                    "id": 850006245121695744,
                    "id_str": "850006245121695744",
                    "text": "1/ Today we’re sharing our vision for the future of the Twitter API platform!nhttps://t.co/XweGngmxlP",
                    "truncated": False,
                    "entities": {
                        "hashtags": [],
                        "symbols": [],
                        "user_mentions": [],
                        "urls": [
                            {
                                "url": "https://t.co/XweGngmxlP",
                                "expanded_url": "https://cards.twitter.com/cards/18ce53wgo4h/3xo1c",
                                "display_url": "cards.twitter.com/cards/18ce53wg…",
                                "indices": [78, 101],
                            }
                        ],
                    },
                    "source": '<a href="http://twitter.com" rel="nofollow">Twitter Web Client</a>',
                    "in_reply_to_status_id": None,
                    "in_reply_to_status_id_str": None,
                    "in_reply_to_user_id": None,
                    "in_reply_to_user_id_str": None,
                    "in_reply_to_screen_name": None,
                    "user": {
                        "id": 2244994945,
                        "id_str": "2244994945",
                        "name": "TwitterDev",
                        "screen_name": "TwitterDev",
                        "location": "Internet",
                        "description": "Your official source for Twitter Platform news, updates & events. Need technical help? Visit https://t.co/mGHnxZCxkt ⌨️  #TapIntoTwitter",
                        "url": "https://t.co/66w26cua1O",
                        "entities": {
                            "url": {
                                "urls": [
                                    {
                                        "url": "https://t.co/66w26cua1O",
                                        "expanded_url": "https://dev.twitter.com/",
                                        "display_url": "dev.twitter.com",
                                        "indices": [0, 23],
                                    }
                                ]
                            },
                            "description": {
                                "urls": [
                                    {
                                        "url": "https://t.co/mGHnxZCxkt",
                                        "expanded_url": "https://twittercommunity.com/",
                                        "display_url": "twittercommunity.com",
                                        "indices": [93, 116],
                                    }
                                ]
                            },
                        },
                        "protected": False,
                        "followers_count": 465425,
                        "friends_count": 1523,
                        "listed_count": 1168,
                        "created_at": "Sat Dec 14 04:35:55 +0000 2013",
                        "favourites_count": 2098,
                        "utc_offset": -25200,
                        "time_zone": "Pacific Time (US & Canada)",
                        "geo_enabled": True,
                        "verified": True,
                        "statuses_count": 3031,
                        "lang": "en",
                        "contributors_enabled": False,
                        "is_translator": False,
                        "is_translation_enabled": False,
                        "profile_background_color": "FFFFFF",
                        "profile_background_image_url": "http://abs.twimg.com/images/themes/theme1/bg.png",
                        "profile_background_image_url_https": "https://abs.twimg.com/images/themes/theme1/bg.png",
                        "profile_background_tile": False,
                        "profile_image_url": "http://pbs.twimg.com/profile_images/530814764687949824/npQQVkq8_normal.png",
                        "profile_image_url_https": "https://pbs.twimg.com/profile_images/530814764687949824/npQQVkq8_normal.png",
                        "profile_banner_url": "https://pbs.twimg.com/profile_banners/2244994945/1396995246",
                        "profile_link_color": "0084B4",
                        "profile_sidebar_border_color": "FFFFFF",
                        "profile_sidebar_fill_color": "DDEEF6",
                        "profile_text_color": "333333",
                        "profile_use_background_image": False,
                        "has_extended_profile": False,
                        "default_profile": False,
                        "default_profile_image": False,
                        "following": True,
                        "follow_request_sent": False,
                        "notifications": False,
                        "translator_type": "regular",
                    },
                    "geo": None,
                    "coordinates": None,
                    "place": None,
                    "contributors": None,
                    "is_quote_status": False,
                    "retweet_count": 284,
                    "favorite_count": 399,
                    "favorited": False,
                    "retweeted": False,
                    "possibly_sensitive": False,
                    "lang": "en",
                },
                "is_quote_status": False,
                "retweet_count": 284,
                "favorite_count": 0,
                "favorited": False,
                "retweeted": False,
                "possibly_sensitive": False,
                "lang": "en",
            },
            {
                "created_at": "Mon Apr 03 16:09:50 +0000 2017",
                "id": 848930551989915648,
                "id_str": "848930551989915648",
                "text": "RT @TwitterMktg: Starting today, businesses can request and share locations when engaging with people in Direct Messages. https://t.co/rpYn…",
                "truncated": False,
                "entities": {
                    "hashtags": [],
                    "symbols": [],
                    "user_mentions": [
                        {
                            "screen_name": "TwitterMktg",
                            "name": "Twitter Marketing",
                            "id": 357750891,
                            "id_str": "357750891",
                            "indices": [3, 15],
                        }
                    ],
                    "urls": [],
                },
                "source": '<a href="http://twitter.com" rel="nofollow">Twitter Web Client</a>',
                "in_reply_to_status_id": None,
                "in_reply_to_status_id_str": None,
                "in_reply_to_user_id": None,
                "in_reply_to_user_id_str": None,
                "in_reply_to_screen_name": None,
                "user": {
                    "id": 6253282,
                    "id_str": "6253282",
                    "name": "Twitter API",
                    "screen_name": "twitterapi",
                    "location": "San Francisco, CA",
                    "description": "The Real Twitter API. I tweet about API changes, service issues and happily answer questions about Twitter and our API. Don't get an answer? It's on my website.",
                    "url": "http://t.co/78pYTvWfJd",
                    "entities": {
                        "url": {
                            "urls": [
                                {
                                    "url": "http://t.co/78pYTvWfJd",
                                    "expanded_url": "https://dev.twitter.com",
                                    "display_url": "dev.twitter.com",
                                    "indices": [0, 22],
                                }
                            ]
                        },
                        "description": {"urls": []},
                    },
                    "protected": False,
                    "followers_count": 6172353,
                    "friends_count": 46,
                    "listed_count": 13091,
                    "created_at": "Wed May 23 06:01:13 +0000 2007",
                    "favourites_count": 26,
                    "utc_offset": -25200,
                    "time_zone": "Pacific Time (US & Canada)",
                    "geo_enabled": True,
                    "verified": True,
                    "statuses_count": 3583,
                    "lang": "en",
                    "contributors_enabled": False,
                    "is_translator": False,
                    "is_translation_enabled": False,
                    "profile_background_color": "C0DEED",
                    "profile_background_image_url": "http://pbs.twimg.com/profile_background_images/656927849/miyt9dpjz77sc0w3d4vj.png",
                    "profile_background_image_url_https": "https://pbs.twimg.com/profile_background_images/656927849/miyt9dpjz77sc0w3d4vj.png",
                    "profile_background_tile": True,
                    "profile_image_url": "http://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3_normal.png",
                    "profile_image_url_https": "https://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3_normal.png",
                    "profile_banner_url": "https://pbs.twimg.com/profile_banners/6253282/1431474710",
                    "profile_link_color": "0084B4",
                    "profile_sidebar_border_color": "C0DEED",
                    "profile_sidebar_fill_color": "DDEEF6",
                    "profile_text_color": "333333",
                    "profile_use_background_image": True,
                    "has_extended_profile": False,
                    "default_profile": False,
                    "default_profile_image": False,
                    "following": True,
                    "follow_request_sent": False,
                    "notifications": False,
                    "translator_type": "regular",
                },
                "geo": None,
                "coordinates": None,
                "place": None,
                "contributors": None,
                "retweeted_status": {
                    "created_at": "Mon Apr 03 16:05:05 +0000 2017",
                    "id": 848929357519241216,
                    "id_str": "848929357519241216",
                    "text": "Starting today, businesses can request and share locations when engaging with people in Direct Messages. https://t.co/rpYndqWfQw",
                    "truncated": False,
                    "entities": {
                        "hashtags": [],
                        "symbols": [],
                        "user_mentions": [],
                        "urls": [
                            {
                                "url": "https://t.co/rpYndqWfQw",
                                "expanded_url": "https://cards.twitter.com/cards/5wzucr/3x700",
                                "display_url": "cards.twitter.com/cards/5wzucr/3…",
                                "indices": [105, 128],
                            }
                        ],
                    },
                    "source": '<a href="https://ads.twitter.com" rel="nofollow">Twitter Ads</a>',
                    "in_reply_to_status_id": None,
                    "in_reply_to_status_id_str": None,
                    "in_reply_to_user_id": None,
                    "in_reply_to_user_id_str": None,
                    "in_reply_to_screen_name": None,
                    "user": {
                        "id": 357750891,
                        "id_str": "357750891",
                        "name": "Twitter Marketing",
                        "screen_name": "TwitterMktg",
                        "location": "Twitter HQ ",
                        "description": "Twitter’s place for marketers, agencies, and creative thinkers ⭐ Bringing you insights, news, updates, and inspiration. Visit @TwitterAdsHelp for Ads support.",
                        "url": "https://t.co/Tfo4moo92y",
                        "entities": {
                            "url": {
                                "urls": [
                                    {
                                        "url": "https://t.co/Tfo4moo92y",
                                        "expanded_url": "https://marketing.twitter.com",
                                        "display_url": "marketing.twitter.com",
                                        "indices": [0, 23],
                                    }
                                ]
                            },
                            "description": {"urls": []},
                        },
                        "protected": False,
                        "followers_count": 924546,
                        "friends_count": 661,
                        "listed_count": 3893,
                        "created_at": "Thu Aug 18 21:08:15 +0000 2011",
                        "favourites_count": 1934,
                        "utc_offset": -25200,
                        "time_zone": "Pacific Time (US & Canada)",
                        "geo_enabled": True,
                        "verified": True,
                        "statuses_count": 6329,
                        "lang": "en",
                        "contributors_enabled": False,
                        "is_translator": False,
                        "is_translation_enabled": False,
                        "profile_background_color": "C0DEED",
                        "profile_background_image_url": "http://pbs.twimg.com/profile_background_images/662767273/jvmxdpdrplhxcw8yvkv2.png",
                        "profile_background_image_url_https": "https://pbs.twimg.com/profile_background_images/662767273/jvmxdpdrplhxcw8yvkv2.png",
                        "profile_background_tile": True,
                        "profile_image_url": "http://pbs.twimg.com/profile_images/800953549697888256/UlXXL5h5_normal.jpg",
                        "profile_image_url_https": "https://pbs.twimg.com/profile_images/800953549697888256/UlXXL5h5_normal.jpg",
                        "profile_banner_url": "https://pbs.twimg.com/profile_banners/357750891/1487188210",
                        "profile_link_color": "19CF86",
                        "profile_sidebar_border_color": "FFFFFF",
                        "profile_sidebar_fill_color": "DDEEF6",
                        "profile_text_color": "333333",
                        "profile_use_background_image": True,
                        "has_extended_profile": False,
                        "default_profile": False,
                        "default_profile_image": False,
                        "following": False,
                        "follow_request_sent": False,
                        "notifications": False,
                        "translator_type": "none",
                    },
                    "geo": None,
                    "coordinates": None,
                    "place": None,
                    "contributors": None,
                    "is_quote_status": False,
                    "retweet_count": 111,
                    "favorite_count": 162,
                    "favorited": False,
                    "retweeted": False,
                    "possibly_sensitive": False,
                    "lang": "en",
                },
                "is_quote_status": False,
                "retweet_count": 111,
                "favorite_count": 0,
                "favorited": False,
                "retweeted": False,
                "lang": "en",
            },
        ],
    )

    res = twitter.twitter(event.text, event.reply, event.conn)

    assert res == (
        "✓@\x02TwitterAPI\x02 (Twitter API): RT @TwitterDev: 1/ Today we’re sharing "
        "our vision for the future of the Twitter API "
        "platform!nhttps://t.co/XweGngmxlP (2 years and 4 months ago)"
    )
    assert event.mock_calls == []


def test_twitter_url(mock_requests, mock_conn):
    twitter.container.api = None
    bot = mock_conn.bot

    result = twitter.twitter_url(
        twitter.TWITTER_RE.search("twitter.com/FakeUser/status/11235"),
        mock_conn,
    )

    assert result is None

    twitter.set_api(bot)

    with pytest.raises(tweepy.TweepError):
        twitter.twitter_url(
            twitter.TWITTER_RE.search("twitter.com/FakeUser/status/11235"),
            mock_conn,
        )

    mock_requests.add(
        "GET",
        "https://api.twitter.com/1.1/statuses/show.json"
        "?id=11235&tweet_mode=extended",
        json={
            "errors": [
                {
                    "message": "No status found with that ID.",
                    "code": 144,
                }
            ],
        },
        status=404,
    )

    result = twitter.twitter_url(
        twitter.TWITTER_RE.search("twitter.com/FakeUser/status/11235"),
        mock_conn,
    )

    assert result is None
