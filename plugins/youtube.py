import re
from typing import Iterable, Mapping, Match, Optional, Union

import isodate
import requests
from requests import Response

from cloudbot import hook
from cloudbot.bot import bot
from cloudbot.util import colors, timeformat
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
    def __init__(
        self, message: str, response: Optional[Union[str, Response]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.response = response


class NoApiKeyError(APIError):
    def __init__(self) -> None:
        super().__init__("Missing API key")


class NoResultsError(APIError):
    def __init__(self, response: Response) -> None:
        super().__init__("No results", response)


def raise_api_errors(response: requests.Response) -> None:
    try:
        response.raise_for_status()
    except requests.RequestException as e:
        try:
            data = response.json()
        except ValueError:
            raise e from None

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
    return "https://youtu.be/{}".format(video_id)


ParamValues = Union[int, str]
ParamMap = Mapping[str, ParamValues]
Parts = Iterable[str]


def do_request(
    method: str,
    parts: Parts,
    params: Optional[ParamMap] = None,
    **kwargs: ParamValues,
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
        raise NoResultsError(request)

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

    like_data = statistics.get("likeCount")
    dislike_data = statistics.get("dislikeCount")

    if like_data:
        # format
        likes = int(like_data)
        out += " - {}".format(pluralize_suffix(likes, "like"))
        if dislike_data:
            dislikes = int(dislike_data)
            total_votes = likes + dislikes
            percent = 100 * likes / total_votes
            out += ", {} (\x02{:.1f}\x02%)".format(
                pluralize_suffix(dislikes, "dislike"), percent
            )

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
        raise NoResultsError(request)

    video_id = json["items"][0]["id"]["videoId"]  # type: str
    return video_id


@hook.regex(youtube_re)
def youtube_url(match: Match[str]) -> Optional[str]:
    try:
        return get_video_description(match.group(1))
    except NoResultsError:
        return None


@hook.command("youtube", "you", "yt", "y")
def youtube(text: str, reply) -> str:
    """<query> - Returns the first YouTube search result for <query>.

    :param text: User input
    """
    try:
        video_id = get_video_id(text)
        return (
            get_video_description(video_id) + " - " + make_short_url(video_id)
        )
    except NoResultsError as e:
        return e.message
    except APIError as e:
        reply(e.message)
        raise


@hook.command("youtime", "ytime")
def youtime(text: str, reply) -> str:
    """<query> - Gets the total run time of the first YouTube search result for <query>."""
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

    return (
        "The video \x02{}\x02 has a length of {} and has been viewed {:,} times for "
        "a total run time of {}!".format(
            snippet["title"], length_text, views, total_text
        )
    )


@hook.regex(ytpl_re)
def ytplaylist_url(match: Match[str]) -> Optional[str]:
    location = match.group(4).split("=")[-1]
    request = get_playlist(location, ["contentDetails", "snippet"])
    raise_api_errors(request)

    json = request.json()

    data = json["items"]
    if not data:
        return None

    item = data[0]
    snippet = item["snippet"]
    content_details = item["contentDetails"]

    title = snippet["title"]
    author = snippet["channelTitle"]
    num_videos = int(content_details["itemCount"])
    count_videos = " - \x02{:,}\x02 video{}".format(
        num_videos, "s"[num_videos == 1 :]
    )
    return "\x02{}\x02 {} - \x02{}\x02".format(title, count_videos, author)
