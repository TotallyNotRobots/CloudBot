import re

import isodate
import requests

from cloudbot import hook
from cloudbot.bot import bot
from cloudbot.util import colors, timeformat
from cloudbot.util.formatting import pluralize_auto

youtube_re = re.compile(
    r'(?:youtube.*?(?:v=|/v/)|youtu\.be/|yooouuutuuube.*?id=)([-_a-zA-Z0-9]+)', re.I
)

base_url = 'https://www.googleapis.com/youtube/v3/'
api_url = base_url + 'videos?part=contentDetails%2C+snippet%2C+statistics&id={}&key={}'
search_api_url = base_url + 'search?part=id&maxResults=1'
playlist_api_url = base_url + 'playlists?part=snippet%2CcontentDetails%2Cstatus'
video_url = "http://youtu.be/%s"


class APIError(Exception):
    def __init__(self, message, response=None):
        super().__init__(message)
        self.message = message
        self.response = response


class NoApiKeyError(APIError):
    def __init__(self):
        super().__init__("Missing API key")


class NoResultsError(APIError):
    def __init__(self):
        super().__init__("No results")


def handle_api_errors(response):
    try:
        response.raise_for_status()
    except requests.RequestException as e:
        try:
            data = response.json()
        except ValueError:
            raise e

        errors = data.get('errors')
        if not errors:
            return

        first_error = errors[0]
        domain = first_error['domain']
        reason = first_error['reason']
        raise APIError("API Error ({}/{})".format(domain, reason), data) from e


def get_video_description(video_id):
    dev_key = bot.config.get_api_key("google_dev_key")
    request = requests.get(api_url.format(video_id, dev_key))
    json = request.json()

    handle_api_errors(request)

    data = json['items']
    if not data:
        return None

    snippet = data[0]['snippet']
    statistics = data[0]['statistics']
    content_details = data[0]['contentDetails']

    out = '\x02{}\x02'.format(snippet['title'])

    if not content_details.get('duration'):
        return out

    length = isodate.parse_duration(content_details['duration'])
    out += ' - length \x02{}\x02'.format(
        timeformat.format_time(int(length.total_seconds()), simple=True)
    )
    try:
        total_votes = float(statistics['likeCount']) + float(statistics['dislikeCount'])
    except (LookupError, ValueError):
        total_votes = 0

    if total_votes != 0:
        # format
        likes = pluralize_auto(int(statistics['likeCount']), "like")
        dislikes = pluralize_auto(int(statistics['dislikeCount']), "dislike")

        percent = 100 * float(statistics['likeCount']) / total_votes
        out += ' - {}, {} (\x02{:.1f}\x02%)'.format(likes, dislikes, percent)

    if 'viewCount' in statistics:
        views = int(statistics['viewCount'])
        out += ' - \x02{:,}\x02 view{}'.format(views, "s"[views == 1 :])

    uploader = snippet['channelTitle']

    upload_time = isodate.parse_datetime(snippet['publishedAt'])
    out += ' - \x02{}\x02 on \x02{}\x02'.format(
        uploader, upload_time.strftime("%Y.%m.%d")
    )

    try:
        yt_rating = content_details['contentRating']['ytRating']
    except KeyError:
        pass
    else:
        if yt_rating == "ytAgeRestricted":
            out += colors.parse(' - $(red)NSFW$(reset)')

    return out


def get_video_id(text):
    dev_key = bot.config.get_api_key('google_dev_key')
    if not dev_key:
        raise NoApiKeyError()

    try:
        request = requests.get(
            search_api_url, params={'q': text, 'key': dev_key, 'type': 'video'}
        )
    except requests.RequestException as e:
        raise APIError("Unable to connect to API") from e

    json = request.json()

    handle_api_errors(request)

    if not json.get('items'):
        raise NoResultsError()

    video_id = json['items'][0]['id']['videoId']
    return video_id


@hook.regex(youtube_re)
def youtube_url(match):
    return get_video_description(match.group(1))


@hook.command("youtube", "you", "yt", "y")
def youtube(text, reply):
    """<query> - Returns the first YouTube search result for <query>."""
    try:
        video_id = get_video_id(text)
        return get_video_description(video_id) + " - " + video_url % video_id
    except APIError as e:
        reply(e.message)
        raise


@hook.command("youtime", "ytime")
def youtime(text, reply):
    """<query> - Gets the total run time of the first YouTube search result for <query>."""
    dev_key = bot.config.get_api_key('google_dev_key')
    try:
        video_id = get_video_id(text)
        request = requests.get(api_url.format(video_id, dev_key))
        handle_api_errors(request)
    except APIError as e:
        reply(e.message)
        raise

    json = request.json()

    data = json['items']
    snippet = data[0]['snippet']
    content_details = data[0]['contentDetails']
    statistics = data[0]['statistics']

    if not content_details.get('duration'):
        return

    length = isodate.parse_duration(content_details['duration'])
    l_sec = int(length.total_seconds())
    views = int(statistics['viewCount'])
    total = int(l_sec * views)

    length_text = timeformat.format_time(l_sec, simple=True)
    total_text = timeformat.format_time(total, accuracy=8)

    return (
        'The video \x02{}\x02 has a length of {} and has been viewed {:,} times for '
        'a total run time of {}!'.format(
            snippet['title'], length_text, views, total_text
        )
    )


ytpl_re = re.compile(
    r'(.*:)//(www.youtube.com/playlist|youtube.com/playlist)(:[0-9]+)?(.*)', re.I
)


@hook.regex(ytpl_re)
def ytplaylist_url(match):
    location = match.group(4).split("=")[-1]
    dev_key = bot.config.get_api_key("google_dev_key")
    request = requests.get(playlist_api_url, params={"id": location, "key": dev_key})
    handle_api_errors(request)

    json = request.json()

    data = json['items']
    if not data:
        return

    snippet = data[0]['snippet']
    content_details = data[0]['contentDetails']

    title = snippet['title']
    author = snippet['channelTitle']
    num_videos = int(content_details['itemCount'])
    count_videos = ' - \x02{:,}\x02 video{}'.format(num_videos, "s"[num_videos == 1 :])
    return "\x02{}\x02 {} - \x02{}\x02".format(title, count_videos, author)
