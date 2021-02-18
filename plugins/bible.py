import requests

from cloudbot import hook


@hook.command("bible", "passage", singlethread=True)
def bible(text, reply):
    """<passage> - Prints the specified passage from the Bible"""
    passage = text.strip()
    params = {"passage": passage, "formatting": "plain", "type": "json"}
    try:
        r = requests.get("https://labs.bible.org/api", params=params)
        r.raise_for_status()
        response = r.json()[0]
    except Exception:
        reply(
            "Something went wrong, either you entered an invalid passage or the API is down."
        )
        raise

    book = response["bookname"]
    ch = response["chapter"]
    ver = response["verse"]
    txt = response["text"]
    return "\x02{} {}:{}\x02 {}".format(book, ch, ver, txt)
