import re
from typing import Iterable, Mapping, Match, Optional, Union

import isodate
import requests

from cloudbot import hook
from cloudbot.bot import bot
from cloudbot.util import colors, formatting, timeformat
from cloudbot.util.formatting import pluralize_suffix

youtube_re = re.compile(
    r"(?:youtube.*?(?:v=|/v/)|youtu\.be/|yooouuutuuube.*?id=)([-_a-zA-Z0-9]+)",
    re.I,
)
ytpl_re = re.compile(
    r"(.*:)//(www.youtube.com/playlist|youtube.com/playlist)(:[0-9]+)?(.*)",
    re.I,
)


base_url = "https://www.googleapis.com/youtube/v3/"


class APIError(Exception):
    def __init__(self, message: str, response: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.response = response


class NoApiKeyError(APIError):
    def __init__(self) -> None:
        super().__init__("Missing API key")


class NoResultsError(APIError):
    def __init__(self) -> None:
        super().__init__("No results")


def raise_api_errors(response: requests.Response) -> None:
    try:
        response.raise_for_status()
    except requests.RequestException as e:
        try:
            data = response.json()
        except ValueError:
            raise e

        errors = data.get("errors")
        if not errors:
            errors = data.get("error", {}).get("errors")

        if not errors:
            return

        first_error = errors[0]
        domain = first_error["domain"]
        reason = first_error["reason"]
        raise APIError("API Error ({}/{})".format(domain, reason), data) from e


def make_short_url(video_id: str) -> str:
    return "http://youtu.be/{}".format(video_id)


ParamValues = Union[int, str]
ParamMap = Mapping[str, ParamValues]
Parts = Iterable[str]


def do_request(
    method: str,
    parts: Parts,
    params: Optional[ParamMap] = None,
    **kwargs: ParamValues
) -> requests.Response:
    api_key = bot.config.get_api_key("google_dev_key")
    if not api_key:
        raise NoApiKeyError()

    if params:
        kwargs.update(params)

    kwargs["part"] = ",".join(parts)
    kwargs["key"] = api_key
    return requests.get(base_url + method, kwargs)


def get_video(video_id: str, parts: Parts) -> requests.Response:
    return do_request("videos", parts, params={"maxResults": 1, "id": video_id})


def get_playlist(playlist_id: str, parts: Parts) -> requests.Response:
    return do_request(
        "playlists", parts, params={"maxResults": 1, "id": playlist_id}
    )


def do_search(term: str, result_type: str = "video") -> requests.Response:
    return do_request(
        "search",
        ["snippet"],
        params={"maxResults": 1, "q": term, "type": result_type},
    )


def get_video_description(video_id: str) -> str:
    parts = ["statistics", "contentDetails", "snippet"]
    request = get_video(video_id, parts)
    raise_api_errors(request)

    json = request.json()

    data = json["items"]
    if not data:
        raise NoResultsError()

    item = data[0]
    snippet = item["snippet"]
    statistics = item["statistics"]
    content_details = item["contentDetails"]

    out = "\x02{}\x02".format(snippet["title"])

    if not content_details.get("duration"):
        return out

    length = isodate.parse_duration(content_details["duration"])
    out += " - length \x02{}\x02".format(
        timeformat.format_time(int(length.total_seconds()), simple=True)
    )

    like_count = int(statistics.get("likeCount", 0))
    dislike_count = int(statistics.get("dislikeCount", 0))
    total_votes = like_count + dislike_count

    if total_votes != 0:
        # format
        likes = pluralize_suffix(int(like_count), "like")
        dislikes = pluralize_suffix(int(dislike_count), "dislike")

        percent = 100 * float(like_count) / total_votes
        out += " - {}, {} (\x02{:.1f}\x02%)".format(likes, dislikes, percent)

    if "viewCount" in statistics:
        views = int(statistics["viewCount"])
        out += " - \x02{:,}\x02 view{}".format(views, "s"[views == 1 :])

    uploader = snippet["channelTitle"]

    upload_time = isodate.parse_datetime(snippet["publishedAt"])
    out += " - \x02{}\x02 on \x02{}\x02".format(
        uploader, upload_time.strftime("%Y.%m.%d")
    )

    try:
        yt_rating = content_details["contentRating"]["ytRating"]
    except KeyError:
        pass
    else:
        if yt_rating == "ytAgeRestricted":
            out += colors.parse(" - $(red)NSFW$(reset)")

    return out


def get_video_id(text: str) -> str:
    try:
        request = do_search(text)
    except requests.RequestException as e:
        raise APIError("Unable to connect to API") from e

    raise_api_errors(request)
    json = request.json()

    if not json.get("items"):
        raise NoResultsError()

    video_id = json["items"][0]["id"]["videoId"]  # type: str
    return video_id


@hook.regex(youtube_re)
def youtube_url(match: Match[str]) -> str:
    return get_video_description(match.group(1))


@hook.command("youtube", "you", "yt", "y")
def youtube(text: str, reply) -> str:
    """<query> - Returns the first YouTube search result for <query>."""
    try:
        video_id = get_video_id(text)
        return "{} - {}".format(
            get_video_description(video_id), make_short_url(video_id)
        )
    except NoResultsError as e:
        return e.message
    except APIError as e:
        reply(e.message)
        raise


@hook.command("youtime", "ytime")
def youtime(text: str, reply) -> str:
    """
    <query> - Gets the total run time of the first YouTube search result
    for <query>.
    """
    parts = ["statistics", "contentDetails", "snippet"]
    try:
        video_id = get_video_id(text)
        request = get_video(video_id, parts)
        raise_api_errors(request)
    except NoResultsError as e:
        return e.message
    except APIError as e:
        reply(e.message)
        raise

    json = request.json()

    data = json["items"]
    item = data[0]
    snippet = item["snippet"]
    content_details = item["contentDetails"]
    statistics = item["statistics"]

    duration = content_details.get("duration")
    if not duration:
        return "Missing duration in API response"

    length = isodate.parse_duration(duration)
    l_sec = int(length.total_seconds())
    views = int(statistics["viewCount"])
    total = int(l_sec * views)

    length_text = timeformat.format_time(l_sec, simple=True)
    total_text = timeformat.format_time(total, accuracy=8)

    fmt = (
        "The video \x02{}\x02 has a length of {} and has been "
        "viewed {:,} times for "
        "a total run time of {}!"
    )
    return fmt.format(snippet["title"], length_text, views, total_text)


@hook.regex(ytpl_re)
def ytplaylist_url(match: Match[str]) -> str:
    location = match.group(4).split("=")[-1]
    request = get_playlist(location, ["contentDetails", "snippet"])
    raise_api_errors(request)

    json = request.json()

    data = json["items"]
    if not data:
        raise NoResultsError()

    item = data[0]
    snippet = item["snippet"]
    content_details = item["contentDetails"]

    title = snippet["title"]
    author = snippet["channelTitle"]
    num_videos = int(content_details["itemCount"])
    count_videos = formatting.pluralize_suffix(
        num_videos, "video", fmt=colors.parse("$(bold){count:,}$(bold) {name}")
    )
    return "\x02{}\x02 - {} - \x02{}\x02".format(title, count_videos, author)
