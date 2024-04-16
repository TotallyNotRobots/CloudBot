import re
from dataclasses import dataclass
from datetime import datetime, timedelta

import requests
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


def get_first_of_class(node, class_name):
    obj = node.find_class(class_name)
    if obj:
        return obj[0].text_content().strip()
    return ""


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
    user_score = ""
    cowntdown_date = ""
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
            except IndexError:
                release = None
            else:
                # strip extra spaces out of the release date
                release = re.sub(r"\s{2,}", " ", release).strip()

            user_score = get_first_of_class(doc, "metascore_w user")
            countdown = doc.find_class("product_countdown")
            if countdown:
                try:
                    script = (
                        countdown[0]
                        .find_class("countdown_holder")[0]
                        .find("span")
                        .find("script")
                        .text_content()
                    )
                except IndexError:
                    pass
                else:
                    match = re.match(
                        r"^.+(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d).+", script
                    )
                    if match:
                        cowntdown_date = match.group(1)
                        # Get time delta
                        cowntdown_date = datetime.strptime(
                            cowntdown_date, "%Y-%m-%d %H:%M:%S"
                        )
                        cowntdown_date = cowntdown_date - datetime.now()
                        cowntdown_date = str(cowntdown_date).split(".")[0]

    score = get_first_of_class(result, "metascore_w")

    return "[{}] {} - \x02{}/100\x02, {}{}{} - {}".format(
        plat.upper().strip(),
        name.strip(),
        score.strip() or "no score",
        f"user score: \x02{user_score}/10\x02, " if user_score else "",
        (
            f"release: \x02{release}\x02, "
            if release and not cowntdown_date
            else ""
        ),
        f"releases in: \x02{cowntdown_date}\x02" if cowntdown_date else "",
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
        "xbsx",
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

    url = f"http://www.metacritic.com/search/{cat}/{title_safe}/results"

    try:
        request = requests.get(url, headers=headers)
        request.raise_for_status()
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
    ) as e:
        reply(f"Could not get Metacritic info: {e}")
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

        if (
            plat not in game_platforms
            or result_plat.casefold() == plat.casefold()
        ):
            results_array.append(Result(res, result_plat or plat))

    results_queue[chan][nick] = results_array
    return metan(chan, nick)
