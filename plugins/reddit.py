import random
import re
from datetime import datetime

import requests
from yarl import URL

from cloudbot import hook
from cloudbot.util import timeformat, formatting

reddit_re = re.compile(r'.*(//((www\.)?reddit\.com/r|redd\.it)[^ ]+)', re.I)

base_url = "https://reddit.com/r/{}"
short_url = "https://redd.it/{}"


def api_request(url, bot):
    """
    :type url: yarl.URL
    :type bot: cloudbot.bot.CloudBot
    """
    url = url.with_query("").with_scheme("https") / ".json"
    r = requests.get(str(url), headers={'User-Agent': bot.user_agent})
    r.raise_for_status()
    return r.json()


def format_output(item, show_url=False):
    """ takes a reddit post and returns a formatted string """
    item["title"] = formatting.truncate(item["title"], 70)
    item["link"] = short_url.format(item["id"])

    raw_time = datetime.fromtimestamp(int(item["created_utc"]))
    item["timesince"] = timeformat.time_since(raw_time, count=1, simple=True)

    item["comments"] = formatting.pluralize(item["num_comments"], 'comment')
    item["points"] = formatting.pluralize(item["score"], 'point')

    if item["over_18"]:
        item["warning"] = " \x02NSFW\x02"
    else:
        item["warning"] = ""

    if show_url:
        return "\x02{title} : {subreddit}\x02 - {comments}, {points}" \
               " - \x02{author}\x02 {timesince} ago - {link}{warning}".format(**item)
    else:
        return "\x02{title} : {subreddit}\x02 - {comments}, {points}" \
               " - \x02{author}\x02, {timesince} ago{warning}".format(**item)


@hook.regex(reddit_re, singlethread=True)
def reddit_url(match, bot):
    url = match.group(1)
    url = URL(url).with_scheme("https")

    if url.host.endswith("redd.it"):
        response = requests.get(url)
        response.raise_for_status()
        url = URL(response.url).with_scheme("https")

    data = api_request(url, bot)
    item = data[0]["data"]["children"][0]["data"]

    return format_output(item)


@hook.command(autohelp=False, singlethread=True)
def reddit(text, bot, reply):
    """[subreddit] [n] - gets a random post from <subreddit>, or gets the [n]th post in the subreddit"""
    id_num = None

    if text:
        # clean and split the input
        parts = text.lower().strip().split()
        url = base_url.format(parts.pop(0).strip())

        # find the requested post number (if any)
        if parts:
            try:
                id_num = int(parts[0]) - 1
            except ValueError:
                return "Invalid post number."
    else:
        url = "https://reddit.com"

    try:
        data = api_request(URL(url), bot)
    except Exception as e:
        reply("Error: " + str(e))
        raise

    data = data["data"]["children"]

    # get the requested/random post
    if id_num is not None:
        try:
            item = data[id_num]
        except IndexError:
            length = len(data)
            return "Invalid post number. Number must be between 1 and {}.".format(length)
    else:
        item = random.choice(data)

    return format_output(item["data"], show_url=True)
