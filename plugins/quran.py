import requests
from requests import HTTPError

from cloudbot import hook


def statuscheck(status, item):
    """since we are doing this a lot might as well return something more meaningful"""
    if status == 404:
        out = "It appears {} does not exist.".format(item)
    elif status == 503:
        out = "Qur'an API is having problems, it would be best to check back later."
    else:
        out = "Qur'an API returned an error, response: {}".format(status)
    return out


def smart_truncate(content, length=425, suffix="...\n"):
    if len(content) <= length:
        return content

    return (
        content[:length].rsplit(" ", 1)[0]
        + suffix
        + content[:length].rsplit(" ", 1)[1]
        + smart_truncate(content[length:])
    )


@hook.command("quran", "verse", singlethread=True)
def quran(text, message, reply):
    """<verse> - Prints the specified Qur'anic verse(s) and its/their translation(s)"""
    api_url = "http://quranapi.azurewebsites.net/api/verse/"
    chapter = text.split(":")[0]
    verse = text.split(":")[1]
    params = {"chapter": chapter, "number": verse, "lang": "ar"}
    r = requests.get(api_url, params=params)
    try:
        r.raise_for_status()
    except HTTPError as e:
        reply(statuscheck(e.response.status_code, text))
        raise

    if r.status_code != 200:
        return statuscheck(r.status_code, text)
    params["lang"] = "en"
    r2 = requests.get(api_url, params=params)

    try:
        r2.raise_for_status()
    except HTTPError as e:
        reply(statuscheck(e.response.status_code, text))
        raise

    data = r.json()
    data2 = r2.json()
    out = "\x02{}\x02: ".format(text)
    verse = data["Text"]
    out += verse
    message(out)
    translation = smart_truncate(data2["Text"])
    return translation
