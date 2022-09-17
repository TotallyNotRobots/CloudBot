import re

import requests
from dataclasses import dataclass
from lxml import html

from cloudbot import hook
from cloudbot.util.queue import Queue

results_queue = Queue()

# metacritic thinks it's so damn smart blocking my scraper
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, "
    "like Gecko) Chrome/41.0.2228.0 Safari/537.36",
    "Referer": "http://www.metacritic.com/",
}

@dataclass
class Result:
    result: html.HtmlElement
    platform: str



@hook.command("metan", autohelp=False)
def metan(chan, nick):
    """- gets the next result from the last metacritic search"""
    global results_queue
    results = results_queue[chan][nick]
    if len(results) == 0:
        return "No [more] results found."

    result = results.pop()
    plat = result.platform
    result = result.result

    if result is None:
        return "No results found."

    # get the name, release date, and score from the result
    product_title = result.find_class("product_title")[0]
    name = product_title.text_content()
    link = "http://metacritic.com" + product_title.find("a").attrib["href"]

    release = None
    try:
        request = requests.get(link, headers=headers)
        request.raise_for_status()
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError):
        pass
    finally:
        if request.text:
            doc = html.fromstring(request.text)
            try:
                release = (
                    doc.find_class("summary_detail release_data")[0]
                    .find_class("data")[0]
                    .text_content()
                )

                # strip extra spaces out of the release date
                release = re.sub(r"\s{2,}", " ", release).strip()
            except IndexError:
                pass

    try:
        score = result.find_class("metascore_w")[0].text_content()
    except IndexError:
        score = ""

    return "[{}] {} - \x02{}/100\x02, {} - {}".format(
        plat.upper().strip(),
        name.strip(),
        score.strip() or "no score",
        "release: \x02%s\x02" % release if release else "",
        link,
    )

@hook.command("metacritic", "meta")
def metacritic(text, reply, chan, nick):
    """[list|all|movie|tv|album|x360|ps3|pc|gba|ds|3ds|wii|vita|wiiu|xone|xbsx|ps4|ps5] <title> - gets rating for <title> from
    metacritic on the specified medium"""
    global results_queue

    args = text.strip()

    game_platforms = (
        "x360",
        "ps3",
        "pc",
        "gba",
        "ds",
        "3ds",
        "wii",
        "vita",
        "wiiu",
        "xone",
        "xbsz",
        "ps4",
        "ps5",
    )

    all_platforms = game_platforms + ("all", "movie", "tv", "album")
    if args.strip().casefold() == "list".casefold():
        return "Platforms: {}".format(", ".join(all_platforms))

    try:
        plat, title = args.split(" ", 1)
        if plat not in all_platforms:
            # raise the ValueError so that the except block catches it
            # in this case, or in the case of the .split above raising the
            # ValueError, we want the same thing to happen
            raise ValueError
    except ValueError:
        plat = "all"
        title = args

    cat = "game" if plat in game_platforms else plat

    title_safe = requests.utils.quote(title)

    url = "http://www.metacritic.com/search/{}/{}/results".format(cat, title_safe)


    try:
        request = requests.get(url, headers=headers)
        request.raise_for_status()
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
        reply("Could not get Metacritic info: {}".format(e))
        raise

    doc = html.fromstring(request.text)

    if not doc.find_class("search_results"):
        return "No results found."

    # if they specified an invalid search term, the input box will be empty
    if doc.get_element_by_id("primary_search_box").value == "":
        return "Invalid search term."

    results = doc.find_class("result")
    results_array = []
    for res in results:
        # if the result_type div has a platform div, get that one
        result_plat = None
        platform_div = res.find_class("platform")
        if platform_div:
            result_plat = platform_div[0].text_content().strip()
        else:
            result_type = res.find_class("result_type")
            if result_type:
                # otherwise, use the result_type text_content
                result_plat = result_type[0].text_content().strip()

        if plat not in game_platforms or result_plat.casefold() == plat.casefold():
            results_array.append(Result(res, result_plat or plat))

    results_queue[chan][nick] = results_array
    return metan(chan, nick)
