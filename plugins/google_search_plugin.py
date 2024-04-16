import random

import requests

from cloudbot import hook
from cloudbot.util import formatting, http


def api_get(kind, query):
    """Use the RESTful Google Search API"""
    url = (
        "http://ajax.googleapis.com/ajax/services/search/%s?"
        "v=1.0&safe=moderate"
    )
    return http.get_json(url % kind, q=query)


# @hook.command("googleimage", "gis", "image")
def googleimage(text):
    """<query> - returns the first google image result for <query>"""

    parsed = api_get("images", text)
    if not 200 <= parsed["responseStatus"] < 300:
        raise OSError(
            "error searching for images: {}: {}".format(
                parsed["responseStatus"], ""
            )
        )
    if not parsed["responseData"]["results"]:
        return "no images found"
    return random.choice(parsed["responseData"]["results"][:10])["unescapedUrl"]


def google(text):
    """<query> - returns the first google search result for <query>"""

    parsed = api_get("web", text)
    if not 200 <= parsed["responseStatus"] < 300:
        raise OSError(
            "error searching for pages: {}: {}".format(
                parsed["responseStatus"], ""
            )
        )
    if not parsed["responseData"]["results"]:
        return "No fucking results found."

    result = parsed["responseData"]["results"][0]

    title = http.unescape(result["titleNoFormatting"])
    title = formatting.truncate_str(title, 60)
    content = http.unescape(result["content"])

    if not content:
        content = "No description available."
    else:
        content = http.html.fromstring(content).text_content()
        content = formatting.truncate_str(content, 150).replace("\n", "")
    return '{} -- \x02{}\x02: "{}"'.format(
        result["unescapedUrl"], title, content
    )


@hook.command("forecast", "fc")
def forecast(text):
    """<query> - returns the weather forecast result for <query>"""
    response = requests.get(
        f"http://wttr.in/{'+'.join(text.split())}?format=j1"
    )
    if response.status_code == 200:
        try:
            j = response.json()
        except Exception as e:
            return f"Error: {e}" + " -- " + response.text
        nearest = j["nearest_area"][0]
        area = nearest["areaName"][0]["value"]
        message = [
            f"{nearest['country'][0]['value']} - {nearest['region'][0]['value']} - {area}, lat: {nearest['latitude']}  long: {nearest['longitude']}"
        ]
        for day in j["weather"]:
            message.append(
                f"\x02{day['date']}\x02 - \x02average\x02: {day['avgtempC']}ºC, \x02max\x02: {day['maxtempC']}ºC, \x02min\x02: {day['mintempC']}ºC, \x02sun hours\x02: {day['sunHour']}, \x02precipitation\x02: {round(sum([float(h['precipMM']) for h in day['hourly']]), 3)}mm \x02"
            )
        return message
    else:
        return "City not found."


@hook.command("astronomy", "ast")
def astronomy(text):
    """<query> - returns the astronomy result for <query>"""
    response = requests.get(
        f"http://wttr.in/{'+'.join(text.split())}?format=j1"
    )
    if response.status_code == 200:
        j = response.json()
        nearest = j["nearest_area"][0]
        message = [
            f"{nearest['country'][0]['value']} - {nearest['region'][0]['value']}, lat: {nearest['latitude']}  long: {nearest['longitude']}"
        ]
        for day in j["weather"]:
            ast = day["astronomy"][0]
            MOONS = {
                "First Quarter": "🌓",
                "Last Quarter": "🌗",
                "Third Quarter": "🌗",
                "Crescent Moon": "🌒",
                "Full Moon": "🌕",
                "New Moon": "🌑",
                "Crescent": "🌒",
                "Full": "🌕",
                "New": "🌑",
                "Waxing Gibbous": "🌖",
                "Waxing Crescent": "🌘",
                "Waning Gibbous": "🌔",
                "Waning Crescent": "🌘",
            }
            if ast["moon_phase"] in MOONS:
                moon = MOONS[ast["moon_phase"]] + " "
            message.append(
                f"\x02{day['date']}\x02 - {moon}"
                + ", ".join([f"\x02{key}\x02: {ast[key]}" for key in ast])
            )
        return message
    else:
        return "City not found."


last_results = []


@hook.command("ddg", "g")
def ddg_search(text):
    """<query> - returns the first duckduckgo search result for <query>"""
    global last_results
    from .ddg import search

    results = search(text)
    result = results.pop()
    last_results = results
    return f"{ result['text'] }   ---   \x02{result['url']}\x02"


@hook.command("ddg_next", "gn")
def ddg_gn(text):
    global last_results
    result = last_results.pop()
    if last_results:
        return f"{ result['text'] }   ---   \x02{result['url']}\x02"
    else:
        return "No search results left"
