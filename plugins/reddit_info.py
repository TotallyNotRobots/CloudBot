from collections import defaultdict
from datetime import datetime

import requests
from requests import HTTPError

from cloudbot import hook
from cloudbot.util import colors
from cloudbot.util.formatting import pluralize_auto
from cloudbot.util.pager import paginated_list

search_pages = defaultdict(dict)

user_url = "http://reddit.com/user/{}/"
subreddit_url = "http://reddit.com/r/{}/"
# This agent should be unique for your cloudbot instance
agent = {"User-Agent": "gonzobot a cloudbot (IRCbot) implementation for snoonet.org by /u/bloodygonzo"}


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
    """[page] - if a sub or mod list has lots of results the results are pagintated. If the most recent search is paginated the pages are stored for retreival. If no argument is given the next page will be returned else a page number can be specified."""
    chan_cf = chan.casefold()
    pages = search_pages[conn.name].get(chan_cf)
    if not pages:
        return "There are modlist pages to show."
    if text:
        try:
            index = int(text)
        except ValueError:
            return "Please specify an integer value."
        page = pages[index - 1]
        if page is None:
            return "please specify a valid page number between 1 and {}.".format(len(pages))
        else:
            return page
    else:
        page = pages.next()
        if page is not None:
            return page
        else:
            return "All pages have been shown."


@hook.command("subs", "moderates", singlethread=True)
def moderates(text, chan, conn, reply):
    """<username> - This plugin prints the list of subreddits a user moderates listed in a reddit users profile. Private subreddits will not be listed."""
    user = text
    r = requests.get(user_url.format(user) + "moderated_subreddits.json", headers=agent)
    try:
        r.raise_for_status()
    except HTTPError as e:
        reply(statuscheck(e.response.status_code, user))
        raise

    if r.status_code != 200:
        return statuscheck(r.status_code, user)

    data = r.json()
    subs = data['data']
    out = colors.parse("$(b){}$(b) moderates these public subreddits: ".format(user))
    pager = paginated_list([sub['sr'] for sub in subs])
    search_pages[conn.name][chan.casefold()] = pager
    page = pager.next()
    if len(pager) > 1:
        page[-1] += " .moremod"

    page[0] = out + page[0]
    return page


@hook.command("karma", "ruser", singlethread=True)
def karma(text, reply):
    """<reddituser> - will return the information about the specified reddit username"""
    user = text
    url = user_url + "about.json"
    r = requests.get(url.format(user), headers=agent)
    try:
        r.raise_for_status()
    except HTTPError as e:
        reply(statuscheck(e.response.status_code, user))
        raise

    if r.status_code != 200:
        return statuscheck(r.status_code, user)

    data = r.json()
    data = data['data']

    out = "$(b){}$(b) ".format(user)

    parts = [
        "$(b){:,}$(b) link karma and $(b){:,}$(b) comment karma".format(data['link_karma'], data['comment_karma'])
    ]

    if data['is_gold']:
        parts.append("has reddit gold")

    if data['is_mod']:
        parts.append("moderates a subreddit")

    if data['has_verified_email']:
        parts.append("email has been verified")

    parts.append("cake day is {}".format(datetime.fromtimestamp(data['created_utc']).strftime('%B %d')))

    account_age = datetime.now() - datetime.fromtimestamp(data['created'])
    age = account_age.days
    age_unit = "day"
    if age > 365:
        age //= 365
        age_unit = "year"

    parts.append("redditor for {}.".format(pluralize_auto(age, age_unit)))
    return colors.parse(out + ' | '.join(parts))


@hook.command("cakeday", singlethread=True)
def cake_day(text, reply):
    """<reddituser> - will return the cakeday for the given reddit username."""
    user = text
    url = user_url + "about.json"
    r = requests.get(url.format(user), headers=agent)

    try:
        r.raise_for_status()
    except HTTPError as e:
        reply(statuscheck(e.response.status_code, user))
        raise

    if r.status_code != 200:
        return statuscheck(r.status_code, user)
    data = r.json()
    out = colors.parse("$(b){}'s$(b) ".format(user))
    out += "cake day is {}, ".format(datetime.fromtimestamp(data['data']['created_utc']).strftime('%B %d'))
    account_age = datetime.now() - datetime.fromtimestamp(data['data']['created'])
    age = account_age.days
    age_unit = "day"
    if age > 365:
        age //= 365
        age_unit = "year"
    out += "they have been a redditor for {}.".format(pluralize_auto(age, age_unit))
    return out


def time_format(numdays):
    if numdays >= 365:
        age = (int(numdays / 365), "y")
        if age[0] > 1:
            age = (age[0], "y")
    else:
        age = (numdays, "d")
    return age


@hook.command("submods", "mods", "rmods", singlethread=True)
def submods(text, chan, conn, reply):
    """<subreddit> - prints the moderators of the specified subreddit."""
    sub = text
    if sub.startswith('/r/'):
        sub = sub[3:]
    elif sub.startswith('r/'):
        sub = sub[2:]
    url = subreddit_url + "about/moderators.json"
    r = requests.get(url.format(sub), headers=agent)

    try:
        r.raise_for_status()
    except HTTPError as e:
        reply(statuscheck(e.response.status_code, 'r/' + sub))
        raise

    if r.status_code != 200:
        return statuscheck(r.status_code, 'r/' + sub)
    data = r.json()
    moderators = []
    for mod in data['data']['children']:
        username = mod['name']
        # Showing the modtime makes the message too long for larger subs
        # if you want to show this information add modtime.days to out below
        modtime = datetime.now() - datetime.fromtimestamp(mod['date'])
        modtime = time_format(modtime.days)
        moderators.append("{} ({}{})".format(username, modtime[0], modtime[1]))
    pager = paginated_list(moderators)
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
    sub = text
    if sub.startswith('/r/'):
        sub = sub[3:]
    elif sub.startswith('r/'):
        sub = sub[2:]
    url = subreddit_url + "about.json"
    r = requests.get(url.format(sub), headers=agent)

    try:
        r.raise_for_status()
    except HTTPError as e:
        reply(statuscheck(e.response.status_code, 'r/' + sub))
        raise

    if r.status_code != 200:
        return statuscheck(r.status_code, 'r/' + sub)
    data = r.json()
    if data['kind'] == "Listing":
        return "It appears r/{} does not exist.".format(sub)
    name = data['data']['display_name']
    title = data['data']['title']
    nsfw = data['data']['over18']
    subscribers = data['data']['subscribers']
    active = data['data']['accounts_active']
    sub_age = datetime.now() - datetime.fromtimestamp(data['data']['created'])
    age, age_unit = time_format(sub_age.days)
    out = "/r/$(b){}$(clear) - {} - a community for {}{}, there are {:,} subscribers and {:,} people online now.".format(
        name, title, age, age_unit, subscribers, active
    )
    if nsfw:
        out += " $(red)NSFW$(clear)"
    return colors.parse(out)
