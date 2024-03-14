import random
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict

import requests
from requests import HTTPError
from yarl import URL

from cloudbot import hook
from cloudbot.util import colors, formatting, timeformat
from cloudbot.util.formatting import pluralize_auto
from cloudbot.util.pager import CommandPager, paginated_list

search_pages: Dict[str, Dict[str, CommandPager]] = defaultdict(dict)
user_re = re.compile(r"^(?:/?(?:u(?:ser)?/)?)?(?P<name>.+?)/?$", re.IGNORECASE)
sub_re = re.compile(r"^(?:/?(?:r/)?)?(?P<name>.+?)/?$", re.IGNORECASE)

user_url = "https://reddit.com/user/{}/"
subreddit_url = "https://reddit.com/r/{}/"
short_url = "https://redd.it/{}"
post_url = "https://reddit.com/comments/{}.json"
# This agent should be unique for your cloudbot instance
agent = {
    "User-Agent": "gonzobot a cloudbot (IRCbot) implementation for snoonet.org by /u/bloodygonzo"
}

post_re = re.compile(
    r"""
    (?:\.|[^a-z0-9]|^)  # Don't allow 'fakereddit.com' or anything else
    (?:
        redd\.it|
        reddit\.com/(?:r/[^/\s]+/)?comments
    )
    /([a-z0-9]+)
    """,
    re.IGNORECASE | re.VERBOSE,
)


def get_user(text):
    match = user_re.match(text)
    if match:
        return match.group("name")

    return None


def get_sub(text):
    match = sub_re.match(text)
    if match:
        return match.group("name")

    return None


def api_request(url):
    url = url.with_query("").with_scheme("https") / ".json"
    r = requests.get(str(url), headers=agent)
    r.raise_for_status()
    return r.json()


def get_post(post_id):
    with requests.get(post_url.format(post_id), headers=agent) as response:
        response.raise_for_status()
        return response.json()


def format_output(item, show_url=False):
    """takes a reddit post and returns a formatted string"""
    item["title"] = formatting.truncate(item["title"], 70)
    item["link"] = short_url.format(item["id"])

    raw_time = datetime.fromtimestamp(int(item["created_utc"]))
    item["timesince"] = timeformat.time_since(raw_time, count=1, simple=True)

    item["comments"] = formatting.pluralize_auto(
        item["num_comments"], "comment"
    )
    item["points"] = formatting.pluralize_auto(item["score"], "point")

    if item["over_18"]:
        item["warning"] = colors.parse(" $(b, red)NSFW$(clear)")
    else:
        item["warning"] = ""

    if show_url:
        item["url"] = " - " + item["link"]
    else:
        item["url"] = ""

    return colors.parse(
        "$(b){title} : {subreddit}$(b) - {comments}, {points}"
        " - $(b){author}$(b) {timesince} ago{url}{warning}"
    ).format(**item)


def statuscheck(status, item):
    """since we are doing this a lot might as well return something more meaningful"""
    if status == 404:
        out = "It appears {} does not exist.".format(item)
    elif status == 403:
        out = "Sorry {} is set to private and I cannot access it.".format(item)
    elif status == 429:
        out = "Reddit appears to be rate-limiting me. Please try again in a few minutes."
    elif status == 503:
        out = "Reddit is having problems, it would be best to check back later."
    else:
        out = "Reddit returned an error, response: {}".format(status)
    return out


@hook.command("moremod", autohelp=False)
def moremod(text, chan, conn):
    """[page] - if a sub or mod list has lots of results the results are pagintated. If the most recent search is
    paginated the pages are stored for retreival. If no argument is given the next page will be returned else a page
    number can be specified."""
    chan_cf = chan.casefold()
    pages = search_pages[conn.name].get(chan_cf)
    if not pages:
        return "There are no modlist pages to show."

    return pages.handle_lookup(text)


@hook.regex(post_re, singlethread=True)
def reddit_post_url(match):
    post_id = match.group(1)
    try:
        data = get_post(post_id)
    except HTTPError as e:
        if e.response.status_code in (403, 404):
            return None

        raise

    item = data[0]["data"]["children"][0]["data"]

    return format_output(item)


@hook.command(autohelp=False, singlethread=True)
def reddit(text, reply):
    """[subreddit] [n] - gets a random post from <subreddit>, or gets the [n]th post in the subreddit"""
    id_num = None

    if text:
        # clean and split the input
        parts = text.lower().strip().split()
        sub = get_sub(parts.pop(0).strip())
        url = subreddit_url.format(sub)

        # find the requested post number (if any)
        if parts:
            try:
                id_num = int(parts[0]) - 1
            except ValueError:
                return "Invalid post number."
    else:
        url = "https://reddit.com"

    try:
        data = api_request(URL(url))
    except Exception as e:
        reply("Error: " + str(e))
        raise

    data = data["data"]["children"]

    if not data:
        return "There do not appear to be any posts to show."

    # get the requested/random post
    if id_num is not None:
        try:
            item = data[id_num]
        except IndexError:
            length = len(data)
            return (
                "Invalid post number. Number must be between 1 and {}.".format(
                    length
                )
            )
    else:
        item = random.choice(data)

    return format_output(item["data"], show_url=True)


@hook.command("subs", "moderates", singlethread=True)
def moderates(text, chan, conn, reply):
    """<username> - This plugin prints the list of subreddits a user moderates listed in a reddit users profile.
    Private subreddits will not be listed."""
    user = get_user(text)
    r = requests.get(
        user_url.format(user) + "moderated_subreddits.json", headers=agent
    )
    try:
        r.raise_for_status()
    except HTTPError as e:
        reply(statuscheck(e.response.status_code, user))
        raise

    data = r.json()
    subs = data["data"]
    out = colors.parse(
        "$(b){}$(b) moderates these public subreddits: ".format(user)
    )
    pager = paginated_list([sub["sr"] for sub in subs], pager_cls=CommandPager)
    search_pages[conn.name][chan.casefold()] = pager
    page = pager.next()
    if len(pager) > 1:
        page[-1] += " .moremod"

    page[0] = out + page[0]
    return page


def get_user_data(page, user, reply):
    url = user_url + page
    r = requests.get(url.format(user), headers=agent)
    try:
        r.raise_for_status()
    except HTTPError as e:
        reply(statuscheck(e.response.status_code, user))
        raise

    return r.json()


@hook.command("karma", "ruser", singlethread=True)
def karma(text, reply):
    """<reddituser> - will return the information about the specified reddit username"""
    user = get_user(text)
    data = get_user_data("about.json", user, reply)
    data = data["data"]

    out = "$(b){}$(b) ".format(user)

    parts = [
        "$(b){:,}$(b) link karma and $(b){:,}$(b) comment karma".format(
            data["link_karma"], data["comment_karma"]
        )
    ]

    if data["is_gold"]:
        parts.append("has reddit gold")

    if data["is_mod"]:
        parts.append("moderates a subreddit")

    if data["has_verified_email"]:
        parts.append("email has been verified")

    parts.append(
        "cake day is {}".format(
            datetime.fromtimestamp(data["created_utc"]).strftime("%B %d")
        )
    )

    account_age = datetime.now() - datetime.fromtimestamp(data["created"])
    age = account_age.days
    age_unit = "day"
    if age > 365:
        age //= 365
        age_unit = "year"

    parts.append("redditor for {}.".format(pluralize_auto(age, age_unit)))
    return colors.parse(out + " | ".join(parts))


@hook.command("cakeday", singlethread=True)
def cake_day(text, reply):
    """<reddituser> - will return the cakeday for the given reddit username."""
    user = get_user(text)
    data = get_user_data("about.json", user, reply)
    out = colors.parse("$(b){}'s$(b) ".format(user))
    out += "cake day is {}, ".format(
        datetime.fromtimestamp(data["data"]["created_utc"]).strftime("%B %d")
    )
    account_age = datetime.now() - datetime.fromtimestamp(
        data["data"]["created"]
    )
    age = account_age.days
    age_unit = "day"
    if age > 365:
        age //= 365
        age_unit = "year"
    out += "they have been a redditor for {}.".format(
        pluralize_auto(age, age_unit)
    )
    return out


def time_format(numdays):
    if numdays >= 365:
        age = (int(numdays / 365), "y")
        if age[0] > 1:
            age = (age[0], "y")
    else:
        age = (numdays, "d")
    return age


def get_sub_data(url, sub, reply):
    r = requests.get(url.format(sub), headers=agent)

    try:
        r.raise_for_status()
    except HTTPError as e:
        code = e.response.status_code
        reply(statuscheck(code, "r/" + sub))
        if code not in (404, 403):
            raise

        return None

    return r.json()


@hook.command("submods", "mods", "rmods", singlethread=True)
def submods(text, chan, conn, reply):
    """<subreddit> - prints the moderators of the specified subreddit."""
    sub = get_sub(text)
    url = subreddit_url + "about/moderators.json"
    data = get_sub_data(url, sub, reply)
    if data is None:
        return None

    moderators = []
    for mod in data["data"]["children"]:
        username = mod["name"]
        # Showing the modtime makes the message too long for larger subs
        # if you want to show this information add modtime.days to out below
        _modtime = datetime.now() - datetime.fromtimestamp(mod["date"])
        modtime = time_format(_modtime.days)
        moderators.append("{} ({}{})".format(username, modtime[0], modtime[1]))

    pager = paginated_list(moderators, pager_cls=CommandPager)
    search_pages[conn.name][chan.casefold()] = pager
    page = pager.next()
    if len(pager) > 1:
        page[-1] += " .moremod"

    out = colors.parse("/r/$(b){}$(b) mods: ".format(sub))
    page[0] = out + page[0]

    return page


@hook.command("subinfo", "subreddit", "sub", "rinfo", singlethread=True)
def subinfo(text, reply):
    """<subreddit> - fetches information about the specified subreddit."""
    sub = get_sub(text)
    url = subreddit_url + "about.json"
    data = get_sub_data(url, sub, reply)
    if data is None:
        return None

    if data["kind"] == "Listing":
        return "It appears r/{} does not exist.".format(sub)

    name = data["data"]["display_name"]
    title = data["data"]["title"]
    nsfw = data["data"]["over18"]
    subscribers = data["data"]["subscribers"]
    active = data["data"]["accounts_active"]
    sub_age = datetime.now() - datetime.fromtimestamp(data["data"]["created"])
    age, age_unit = time_format(sub_age.days)
    out = (
        "/r/$(b){}$(clear) - {} - a community for {}{}, there are {:,} subscribers and {:,} people online "
        "now."
    ).format(name, title, age, age_unit, subscribers, active)
    if nsfw:
        out += " $(red)NSFW$(clear)"
    return colors.parse(out)
