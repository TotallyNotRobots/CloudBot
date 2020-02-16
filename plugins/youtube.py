import re
import time

import isodate
import requests

from cloudbot import hook
from cloudbot.bot import bot
from cloudbot.util import timeformat
from cloudbot.util.formatting import pluralize_auto

youtube_re = re.compile(
    r"(?:youtube.*?(?:v=|/v/)|youtu\.be/|yooouuutuuube.*?id=)([-_a-zA-Z0-9]+)", re.I
)

base_url = "https://www.googleapis.com/youtube/v3/"
api_url = base_url + "videos?part=contentDetails%2C+snippet%2C+statistics&id={}&key={}"
search_api_url = base_url + "search?part=id&maxResults=1"
playlist_api_url = base_url + "playlists?part=snippet%2CcontentDetails%2Cstatus"
video_url = "http://youtu.be/%s"
err_no_api = "The YouTube API is off in the Google Developers Console."


class APIError(Exception):
    def __init__(self, message, response=None):
        super().__init__(message)
        self.message = message
        self.response = response


def get_video_description(video_id):
    dev_key = bot.config.get_api_key("google_dev_key")
    request = requests.get(api_url.format(video_id, dev_key))
    json = request.json()

    if json.get("error"):
        if json["error"]["code"] == 403:
            raise APIError(err_no_api, json)

        raise APIError("Unknown error", json)

    data = json["items"]
    if not data:
        return None

    snippet = data[0]["snippet"]
    statistics = data[0]["statistics"]
    content_details = data[0]["contentDetails"]

    out = "\x02{}\x02".format(snippet["title"])

    if not content_details.get("duration"):
        return out

    length = isodate.parse_duration(content_details["duration"])
    out += " - length \x02{}\x02".format(
        timeformat.format_time(int(length.total_seconds()), simple=True)
    )
    try:
        total_votes = float(statistics["likeCount"]) + float(statistics["dislikeCount"])
    except (LookupError, ValueError):
        total_votes = 0

    if total_votes != 0:
        # format
        likes = pluralize_auto(int(statistics["likeCount"]), "like")
        dislikes = pluralize_auto(int(statistics["dislikeCount"]), "dislike")

        percent = 100 * float(statistics["likeCount"]) / total_votes
        out += " - {}, {} (\x02{:.1f}\x02%)".format(likes, dislikes, percent)

    if "viewCount" in statistics:
        views = int(statistics["viewCount"])
        out += " - \x02{:,}\x02 view{}".format(views, "s"[views == 1 :])

    uploader = snippet["channelTitle"]

    upload_time = time.strptime(snippet["publishedAt"], "%Y-%m-%dT%H:%M:%S.000Z")
    out += " - \x02{}\x02 on \x02{}\x02".format(
        uploader, time.strftime("%Y.%m.%d", upload_time)
    )

    if "contentRating" in content_details:
        out += " - \x034NSFW\x02"

    return out


def get_video_id(reply, text):
    dev_key = bot.config.get_api_key("google_dev_key")
    if not dev_key:
        return None, "This command requires a Google Developers Console API key."

    try:
        request = requests.get(
            search_api_url, params={"q": text, "key": dev_key, "type": "video"}
        )
        request.raise_for_status()
    except Exception:
        reply("Error performing search.")
        raise

    json = request.json()

    if json.get("error"):
        if json["error"]["code"] == 403:
            return None, err_no_api

        return None, "Error performing search."

    if not json.get("items"):
        return None, "No results found."

    video_id = json["items"][0]["id"]["videoId"]
    return video_id, None


@hook.regex(youtube_re)
def youtube_url(match):
    return get_video_description(match.group(1))


@hook.command("youtube", "you", "yt", "y")
def youtube(text, reply):
    """<query> - Returns the first YouTube search result for <query>."""
    video_id, err = get_video_id(reply, text)
    if err:
        return err

    try:
        return get_video_description(video_id) + " - " + video_url % video_id
    except APIError as e:
        reply(e.message)
        raise


@hook.command("youtime", "ytime")
def youtime(text, reply):
    """<query> - Gets the total run time of the first YouTube search result for <query>."""
    video_id, err = get_video_id(reply, text)
    if err:
        return err

    dev_key = bot.config.get_api_key("google_dev_key")
    request = requests.get(api_url.format(video_id, dev_key))
    request.raise_for_status()

    json = request.json()

    if json.get("error"):
        return
    data = json["items"]
    snippet = data[0]["snippet"]
    content_details = data[0]["contentDetails"]
    statistics = data[0]["statistics"]

    if not content_details.get("duration"):
        return

    length = isodate.parse_duration(content_details["duration"])
    l_sec = int(length.total_seconds())
    views = int(statistics["viewCount"])
    total = int(l_sec * views)

    length_text = timeformat.format_time(l_sec, simple=True)
    total_text = timeformat.format_time(total, accuracy=8)

    return (
        "The video \x02{}\x02 has a length of {} and has been viewed {:,} times for "
        "a total run time of {}!".format(
            snippet["title"], length_text, views, total_text
        )
    )


ytpl_re = re.compile(
    r"(.*:)//(www.youtube.com/playlist|youtube.com/playlist)(:[0-9]+)?(.*)", re.I
)


@hook.regex(ytpl_re)
def ytplaylist_url(match, reply):
    location = match.group(4).split("=")[-1]
    dev_key = bot.config.get_api_key("google_dev_key")
    try:
        request = requests.get(
            playlist_api_url, params={"id": location, "key": dev_key}
        )
        request.raise_for_status()
    except Exception:
        reply("Error looking up playlist.")
        raise

    json = request.json()

    if json.get("error"):
        if json["error"]["code"] == 403:
            return err_no_api

        return "Error looking up playlist."

    data = json["items"]
    if not data:
        return "No results found."

    snippet = data[0]["snippet"]
    content_details = data[0]["contentDetails"]

    title = snippet["title"]
    author = snippet["channelTitle"]
    num_videos = int(content_details["itemCount"])
    count_videos = " - \x02{:,}\x02 video{}".format(num_videos, "s"[num_videos == 1 :])
    return "\x02{}\x02 {} - \x02{}\x02".format(title, count_videos, author)
