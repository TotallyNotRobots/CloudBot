import datetime

import requests

from cloudbot import hook
from cloudbot.bot import bot
from cloudbot.util.http import parse_xml

base_url = "http://thetvdb.com/api/"


def get_episodes_for_series(series_name, api_key):
    res = {"error": None, "ended": False, "episodes": None, "name": None}
    # http://thetvdb.com/wiki/index.php/API:GetSeries

    try:
        params = {"seriesname": series_name}
        request = requests.get(base_url + "GetSeries.php", params=params)
        request.raise_for_status()
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError):
        res["error"] = "error contacting thetvdb.com"
        return res

    query = parse_xml(request.content)
    series_id = query.xpath("//seriesid/text()")

    if not series_id:
        res["error"] = "Unknown TV series. (using www.thetvdb.com)"
        return res

    series_id = series_id[0]

    try:
        _request = requests.get(
            base_url + "%s/series/%s/all/en.xml" % (api_key, series_id)
        )
        _request.raise_for_status()
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError):
        res["error"] = "error contacting thetvdb.com"
        return res

    series = parse_xml(_request.content)
    try:
        series_name = series.xpath("//SeriesName/text()")[0]
    except LookupError:
        series_name = series.xpath("//SeriesName/text()")

    try:
        if series.xpath("//Status/text()")[0] == "Ended":
            res["ended"] = True
    except LookupError:
        if series.xpath("//Status/text()") == "Ended":
            res["ended"] = True

    res["episodes"] = series.xpath("//Episode")
    res["name"] = series_name
    return res


def get_episode_info(episode):
    first_aired = episode.findtext("FirstAired")

    try:
        air_date = datetime.datetime.strptime(first_aired, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None

    episode_num = "S%02dE%02d" % (
        int(episode.findtext("SeasonNumber")),
        int(episode.findtext("EpisodeNumber")),
    )

    episode_name = episode.findtext("EpisodeName")
    # in the event of an unannounced episode title, users either leave the
    # field out (None) or fill it with TBA
    if episode_name == "TBA":
        episode_name = None

    episode_desc = "{}".format(episode_num)
    if episode_name:
        episode_desc += " - {}".format(episode_name)

    return first_aired, air_date, episode_desc


def get_data(text):
    api_key = bot.config.get_api_key("tvdb")
    if api_key is None:
        return (None, None, None), "error: no api key set"

    data = get_episodes_for_series(text, api_key)

    if data["error"]:
        return (None, None, None), data["error"]

    series_name = data["name"]
    ended = data["ended"]
    episodes = data["episodes"]

    return (series_name, ended, episodes), None


@hook.command()
@hook.command("tv")
def tv_next(text):
    """<series> - Get the next episode of <series>."""
    (series_name, ended, episodes), err = get_data(text)
    if err:
        return err

    if ended:
        return "{} has ended.".format(series_name)

    next_eps = []
    today = datetime.date.today()

    for episode in reversed(episodes):
        ep_info = get_episode_info(episode)

        if ep_info is None:
            continue

        (first_aired, air_date, episode_desc) = ep_info

        if air_date > today:
            next_eps = ["{} ({})".format(first_aired, episode_desc)]
        elif air_date == today:
            next_eps = ["Today ({})".format(episode_desc)] + next_eps
        else:
            # we're iterating in reverse order with newest episodes last
            # so, as soon as we're past today, break out of loop
            break

    if not next_eps:
        return "There are no new episodes scheduled for {}.".format(series_name)

    if len(next_eps) == 1:
        return "The next episode of {} airs {}".format(series_name, next_eps[0])

    return "The next episodes of {}: {}".format(series_name, ", ".join(next_eps))


@hook.command()
@hook.command("tv_prev")
def tv_last(text):
    """<series> - Gets the most recently aired episode of <series>."""
    (series_name, ended, episodes), err = get_data(text)
    if err:
        return err

    prev_ep = None
    today = datetime.date.today()

    for episode in reversed(episodes):
        ep_info = get_episode_info(episode)

        if ep_info is None:
            continue

        (first_aired, air_date, episode_desc) = ep_info

        if air_date < today:
            # iterating in reverse order, so the first episode encountered
            # before today was the most recently aired
            prev_ep = "{} ({})".format(first_aired, episode_desc)
            break

    if not prev_ep:
        return "There are no previously aired episodes for {}.".format(series_name)

    if ended:
        return "{} ended. The last episode aired {}.".format(series_name, prev_ep)

    return "The last episode of {} aired {}.".format(series_name, prev_ep)
