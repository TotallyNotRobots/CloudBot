import html
import random
import re
from datetime import datetime

import tweepy

from cloudbot import hook
from cloudbot.util import timeformat

TWITTER_RE = re.compile(
    r"(?:(?:www.twitter.com|twitter.com)/(?:[-_a-zA-Z0-9]+)/status/)([0-9]+)",
    re.I,
)


def _get_conf_value(conf, field):
    return conf["plugins"]["twitter"][field]


def get_config(conn, field, default):
    try:
        return _get_conf_value(conn.config, field)
    except LookupError:
        try:
            return _get_conf_value(conn.bot.config, field)
        except LookupError:
            return default


def get_tweet_mode(conn, default="extended"):
    return get_config(conn, "tweet_mode", default)


def make_api(bot):
    consumer_key = bot.config.get_api_key("twitter_consumer_key")
    consumer_secret = bot.config.get_api_key("twitter_consumer_secret")

    oauth_token = bot.config.get_api_key("twitter_access_token")
    oauth_secret = bot.config.get_api_key("twitter_access_secret")

    if not all((consumer_key, consumer_secret, oauth_token, oauth_secret)):
        return None

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(oauth_token, oauth_secret)

    return tweepy.API(auth)


class APIContainer:
    api = None


container = APIContainer()

IGNORE_ERRORS = [
    # User not found
    50,
    # User has been suspended
    63,
    # No status found with that ID
    144,
    # Private tweet
    179,
]


@hook.on_start()
def set_api(bot):
    container.api = make_api(bot)


@hook.regex(TWITTER_RE)
def twitter_url(match, conn):
    # Find the tweet ID from the URL
    tweet_id = match.group(1)

    # Get the tweet using the tweepy API
    tw_api = container.api
    if tw_api is None:
        return None

    try:
        tweet = tw_api.get_status(tweet_id, tweet_mode=get_tweet_mode(conn))
    except tweepy.TweepError as e:
        if e.api_code in IGNORE_ERRORS:
            return None

        raise

    user = tweet.user

    return format_tweet(tweet, user)


@hook.command("twitter", "tw", "twatter")
def twitter(text, reply, conn):
    """<user> [n] - Gets last/[n]th tweet from <user>"""

    tw_api = container.api
    if tw_api is None:
        return "This command requires a twitter API key."

    tweet_mode = get_tweet_mode(conn)

    if re.match(r"^\d+$", text):
        # user is getting a tweet by id

        try:
            # get tweet by id
            tweet = tw_api.get_status(text, tweet_mode=tweet_mode)
        except tweepy.error.TweepError as e:
            if "404" in e.reason:
                reply("Could not find tweet.")
            else:
                reply("Error: {}".format(e.reason))

            raise

        user = tweet.user

    elif re.match(r"^\w{1,15}$", text) or re.match(r"^\w{1,15}\s+\d+$", text):
        # user is getting a tweet by name

        if text.find(" ") == -1:
            username = text
            tweet_number = 0
        else:
            username, tweet_number = text.split()
            tweet_number = int(tweet_number) - 1

        if tweet_number > 200:
            return "This command can only find the last \x02200\x02 tweets."

        try:
            # try to get user by username
            user = tw_api.get_user(username, tweet_mode=tweet_mode)
        except tweepy.error.TweepError as e:
            if "404" in e.reason:
                reply("Could not find user.")
            else:
                reply("Error: {}".format(e.reason))
            raise

        # get the users tweets
        user_timeline = tw_api.user_timeline(
            id=user.id, count=tweet_number + 1, tweet_mode=tweet_mode
        )

        # if the timeline is empty, return an error
        if not user_timeline:
            return "The user \x02{}\x02 has no tweets.".format(user.screen_name)

        # grab the newest tweet from the users timeline
        try:
            tweet = user_timeline[tweet_number]
        except IndexError:
            tweet_count = len(user_timeline)
            return "The user \x02{}\x02 only has \x02{}\x02 tweets.".format(
                user.screen_name, tweet_count
            )

    elif re.match(r"^#\w+$", text):
        # user is searching by hashtag
        search = tw_api.search(text, tweet_mode=tweet_mode)

        if not search:
            return "No tweets found."

        tweet = random.choice(search)
        user = tweet.user
    else:
        # ???
        return "Invalid Input"

    return format_tweet(tweet, user)


# Format the return the text of the tweet
def format_tweet(tweet, user):
    try:
        text = tweet.full_text
    except AttributeError:
        text = tweet.text

    text = " ".join(text.split())

    if user.verified:
        prefix = "\u2713"
    else:
        prefix = ""

    time = timeformat.time_since(tweet.created_at, datetime.utcnow())

    return "{}@\x02{}\x02 ({}): {} ({} ago)".format(
        prefix, user.screen_name, user.name, html.unescape(text), time
    )


@hook.command("twuser", "twinfo")
def twuser(text, reply):
    """<user> - Get info on the Twitter user <user>"""

    tw_api = container.api
    if tw_api is None:
        return None

    try:
        # try to get user by username
        user = tw_api.get_user(text)
    except tweepy.error.TweepError as e:
        if "404" in e.reason:
            reply("Could not find user.")
        else:
            reply("Error: {}".format(e.reason))
        raise

    if user.verified:
        prefix = "\u2713"
    else:
        prefix = ""

    if user.location:
        loc_str = " is located in \x02{}\x02 and".format(user.location)
    else:
        loc_str = ""

    if user.description:
        desc_str = ' The users description is "{}"'.format(user.description)
    else:
        desc_str = ""

    return (
        "{}@\x02{}\x02 ({}){} has \x02{:,}\x02 "
        "tweets and \x02{:,}\x02 followers.{}".format(
            prefix,
            user.screen_name,
            user.name,
            loc_str,
            user.statuses_count,
            user.followers_count,
            desc_str,
        )
    )
