import re

from cloudbot import hook
from cloudbot.util import http, timeformat

url_re = re.compile(r"vimeo\.com/([0-9]+)")
api_url = "https://vimeo.com/api/v2/video/{id}.json"


@hook.regex(url_re)
def vimeo_url(match):
    """vimeo <url> - returns information on the Vimeo video at <url>"""
    video_id = match.group(1)
    data = http.get_json(api_url.format(id=video_id))

    if not data:
        return None

    info = data[0]

    info["duration"] = timeformat.format_time(info["duration"])
    info.setdefault("stats_number_of_likes", 0)

    return (
        "\x02{title}\x02 - length \x02{duration}\x02 - "
        "\x02{stats_number_of_likes:,d}\x02 likes - "
        "\x02{stats_number_of_plays:,d}\x02 plays - "
        "\x02{user_name}\x02 on \x02{upload_date}\x02".format_map(info)
    )
