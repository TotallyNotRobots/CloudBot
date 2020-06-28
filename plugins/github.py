import re

import requests

from cloudbot import hook
from cloudbot.util import formatting, web

shortcuts = {}
url_re = re.compile(r"(?:https?://github\.com/)?(?P<owner>[^/]+)/(?P<repo>[^/]+)")


def parse_url(url):
    """
    >>> parse_url("https://github.com/TotallyNotRobots/CloudBot/")
    ('TotallyNotRobots', 'CloudBot')
    >>> parse_url("TotallyNotRobots/CloudBot/")
    ('TotallyNotRobots', 'CloudBot')
    >>> parse_url("TotallyNotRobots/CloudBot")
    ('TotallyNotRobots', 'CloudBot')
    """
    match = url_re.match(url)
    return match.group("owner"), match.group("repo")


@hook.on_start()
def load_shortcuts(bot):
    shortcuts["cloudbot"] = parse_url(bot.repo_link)


@hook.command("ghissue", "issue")
def issue_cmd(text):
    """<username|repo> [number] - gets issue [number]'s summary, or the open issue count if no issue is specified"""
    args = text.split()
    owner, repo = parse_url(args[0] if args[0] not in shortcuts else shortcuts[args[0]])
    issue = args[1] if len(args) > 1 else None

    if issue:
        r = requests.get(
            "https://api.github.com/repos/{}/{}/issues/{}".format(owner, repo, issue)
        )
        r.raise_for_status()
        j = r.json()

        url = web.try_shorten(j["html_url"], service="git.io")
        number = j["number"]
        title = j["title"]
        summary = formatting.truncate(j["body"].split("\n")[0], 25)
        if j["state"] == "open":
            state = "\x033\x02Opened\x02\x0f by {}".format(j["user"]["login"])
        else:
            state = "\x034\x02Closed\x02\x0f by {}".format(j["closed_by"]["login"])

        return "Issue #{} ({}): {} | {}: {}".format(number, state, url, title, summary)
    r = requests.get("https://api.github.com/repos/{}/{}/issues".format(owner, repo))
    r.raise_for_status()
    j = r.json()

    count = len(j)
    if count == 0:
        return "Repository has no open issues."

    return "Repository has {} open issues.".format(count)
