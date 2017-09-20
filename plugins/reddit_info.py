import json

import requests

from collections import defaultdict
from datetime import datetime
from bs4 import BeautifulSoup
from cloudbot import hook
from cloudbot.util import colors
from cloudbot.util.formatting import pluralize

search_pages = defaultdict(list)
search_page_indexes = {}

user_url = "http://reddit.com/user/{}/"
subreddit_url = "http://reddit.com/r/{}/"
# This agent should be unique for your cloudbot instance
agent = {"User-Agent": "gonzobot a cloudbot (IRCbot) implementation for snoonet.org by /u/bloodygonzo"}


def two_lines(bigstring, chan):
    """Receives a string with new lines. Groups the string into a list of strings with up to 2 new lines per string element. Returns first string element then stores the remaining list in search_pages."""
    global search_pages
    temp = bigstring.split('\n')
    for i in range(0, len(temp), 2):
        search_pages[chan].append('\n'.join(temp[i:i+2]))
    search_page_indexes[chan] = 0
    return search_pages[chan][0]


def smart_truncate(content, length=355, suffix='...\n'):
    if len(content) <= length:
        return content
    else:
        return content[:length].rsplit(' \u2022 ', 1)[0]+ suffix + content[:length].rsplit(' \u2022 ', 1)[1] + smart_truncate(content[length:])


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
def moremod(text, chan):
    """if a sub or mod list has lots of results the results are pagintated. If the most recent search is paginated the pages are stored for retreival. If no argument is given the next page will be returned else a page number can be specified."""
    if not search_pages[chan]:
        return "There are modlist pages to show."
    if text:
        try:
            index = int(text)
        except ValueError:
            return "Please specify an integer value."
        if abs(index) > len(search_pages[chan]) or index == 0:
            return "please specify a valid page number between 1 and {}.".format(len(search_pages[chan]))
        else:
            return "{}(page {}/{})".format(search_pages[chan][index-1], index, len(search_pages[chan]))
    else:
        search_page_indexes[chan] += 1
        if search_page_indexes[chan] < len(search_pages[chan]):
            return "{}(page {}/{})".format(search_pages[chan][search_page_indexes[chan]], search_page_indexes[chan] + 1, len(search_pages[chan]))
        else:
            return "All pages have been shown."


@hook.command("subs", "moderates", singlethread=True)
def moderates(text, chan):
    """This plugin prints the list of subreddits a user moderates listed in a reddit users profile. Private subreddits will not be listed."""
    global search_pages
    search_pages[chan] = []
    search_page_indexes[chan] = 0
    user = text
    r = requests.get(user_url.format(user) + "moderated_subreddits.json", headers=agent)
    if r.status_code != 200:
        return statuscheck(r.status_code, user)

    data = r.json()
    subs = data['data']
    out = colors.parse("$(b){}$(b) moderates these public subreddits: ".format(user))
    for sub in subs:
        out += "{} \u2022 ".format(sub['sr'])

    out = out[:-2]
    out = smart_truncate(out)
    if len(out.split('\n')) > 2:
        out = two_lines(out, chan)
        return "{}(page {}/{}) .moremod".format(out, search_page_indexes[chan] + 1, len(search_pages[chan]))
    return out


@hook.command("karma", "ruser", singlethread=True)
def karma(text):
    """karma <reddituser> will return the information about the specified reddit username"""
    user = text
    url = user_url + "about.json"
    r = requests.get(url.format(user), headers=agent)
    if r.status_code != 200:
        return statuscheck(r.status_code, user)
    data = r.json()
    out = "$(b){}$(b) ".format(user)
    out += "$(b){:,}$(b) link karma and ".format(data['data']['link_karma'])
    out += "$(b){:,}$(b) comment karma | ".format(data['data']['comment_karma'])
    if data['data']['is_gold']:
        out += "has reddit gold | "
    if data['data']['is_mod']:
        out += "is a moderator | "
    if data['data']['has_verified_email']:
        out += "email has been verified | "
    out += "cake day is {} | ".format(datetime.fromtimestamp(data['data']['created_utc']).strftime('%B %d'))
    account_age = datetime.now() - datetime.fromtimestamp(data['data']['created'])
    age = account_age.days
    age_unit = "day"
    if age > 365:
        age //= 365
        age_unit = "year"
    out += "redditor for {}.".format(pluralize(age, age_unit))
    return colors.parse(out)


@hook.command("cakeday", singlethread=True)
def cake_day(text):
    """cakeday <reddituser> will return the cakeday for the given reddit username."""
    user = text
    url = user_url + "about.json"
    r = requests.get(url.format(user), headers=agent)
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
    out += "they have been a redditor for {}.".format(pluralize(age, age_unit))
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
def submods(text, chan):
    """submods <subreddit> prints the moderators of the specified subreddit."""
    global search_pages
    search_pages[chan] = []
    search_page_indexes[chan] = 0
    sub = text
    if sub.startswith('/r/'):
        sub = sub[3:]
    elif sub.startswith('r/'):
        sub = sub[2:]
    url = subreddit_url + "about/moderators.json"
    r = requests.get(url.format(sub), headers=agent)
    if r.status_code != 200:
        return statuscheck(r.status_code, 'r/'+sub)
    data = r.json()
    out = colors.parse("/r/$(b){}$(b) mods: ".format(sub))
    for mod in data['data']['children']:
        username = mod['name']
        # Showing the modtime makes the message too long for larger subs
        # if you want to show this information add modtime.days to out below
        modtime = datetime.now() - datetime.fromtimestamp(mod['date'])
        modtime = time_format(modtime.days)
        out += "{} ({}{}) \u2022 ".format(username, modtime[0], modtime[1])
    out = smart_truncate(out)
    out = out[:-3]
    if len(out.split('\n')) > 2:
        out = two_lines(out, chan)
        return "{}(page {}/{}) .moremod".format(out, search_page_indexes[chan] + 1, len(search_pages[chan]))
    return out


@hook.command("subinfo","subreddit", "sub", "rinfo", singlethread=True)
def subinfo(text):
    """subinfo <subreddit> fetches information about the specified subreddit."""
    sub = text
    if sub.startswith('/r/'):
        sub = sub[3:]
    elif sub.startswith('r/'):
        sub = sub[2:]
    url = subreddit_url + "about.json"
    r = requests.get(url.format(sub), headers=agent)
    if r.status_code != 200:
        return statuscheck(r.status_code, 'r/'+sub)
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
