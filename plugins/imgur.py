from __future__ import annotations

import random
import re
from contextlib import suppress
from typing import TYPE_CHECKING

from imgurpython import ImgurClient
from typing_extensions import override

from cloudbot import hook
from cloudbot.util import web

if TYPE_CHECKING:
    from re import Match

    from cloudbot.client import Client


class CustomImgurClient(ImgurClient):
    @override
    def logged_in(self) -> None:
        return None


NO_NSFW = False


class APIContainer:
    api: CustomImgurClient | None = None


container = APIContainer()


def make_api(bot):
    client_id = bot.config.get_api_key("imgur_client_id")
    client_secret = bot.config.get_api_key("imgur_client_secret")

    if not (client_id and client_secret):
        # Either the client id or secret aren't specified
        return None

    return CustomImgurClient(client_id, client_secret)


@hook.on_start()
def set_api(bot) -> None:
    container.api = make_api(bot)


def get_items(text, api: CustomImgurClient):
    reddit_search: Match[str] | None
    if text:
        reddit_search = re.search(r"/r/([^\s/]+)", text)
        user_search = re.search(r"/user/([^\s/]+)", text)

        if reddit_search:
            subreddit = reddit_search.groups()[0]
            items = api.subreddit_gallery(subreddit)
        elif user_search:
            user = user_search.groups()[0]
            items = api.get_account_submissions(user)
        elif text in ("meme", "memes"):
            items = api.memes_subgallery()
        elif text == "random":
            page = random.randint(1, 50)
            items = api.gallery_random(page=page)
        else:
            page = random.randint(1, 5)
            items = api.gallery_search(text, page=page)
    else:
        reddit_search = None
        items = api.gallery()

    if NO_NSFW:
        items = [item for item in items if not item.nsfw]

    return items, bool(reddit_search)


@hook.command(autohelp=False)
def imgur(text):
    """[search term] / [/r/subreddit] / [/user/username] / memes / random - returns a link to a random imgur image based
    on your input. if no input is given the bot will get an image from the imgur frontpage
    """
    text = text.strip().lower()

    if not container.api:
        return "No imgur API details"

    if text == "apicredits":
        return container.api.credits

    items, is_reddit = get_items(text, container.api)

    if not items:
        return "No results found."

    # if the item has no title, we don't want it. ugh >_>
    items = [item for item in items if item.title]

    random.shuffle(items)
    item = random.choice(items)

    tags = []

    # remove unslightly full stops
    if item.title.endswith("."):
        title = item.title[:-1]
    else:
        title = item.title

    # if it's an imgur meme, add the meme name
    # if not, AttributeError will trigger and code will carry on
    with suppress(AttributeError):
        title = f"\x02{item.meme_metadata['meme_name'].lower()}\x02 - {title}"

    # if the item has a tag, show that
    if item.section:
        tags.append(item.section)

    # if the item is nsfw, show that
    if item.nsfw:
        tags.append("nsfw")

    # if the search was a subreddit search, add the reddit comment link
    if is_reddit:
        reddit_url = web.try_shorten(f"http://reddit.com{item.reddit_comments}")
        url = f"{item.link} ({reddit_url})"
    else:
        url = f"{item.link}"

    tag_list = "\x02, \x02".join(tags)
    tag_str = f"[\x02{tag_list}\x02] " if tags else ""

    return f'{tag_str}"{title}" - {url}'


@hook.command("imguralbum", "multiimgur", "imgalbum", "album", autohelp=False)
def imguralbum(text, conn: Client):
    """[search term] / [/r/subreddit] / [/user/username] / memes / random - returns a link to lots of random images
    based on your input. if no input is given the bot will get images from the imgur frontpage
    """
    text = text.strip().lower()

    if not container.api:
        return "No imgur API details"

    if text == "apicredits":
        return container.api.credits

    items, _ = get_items(text, container.api)

    if not items:
        return "No results found."

    random.shuffle(items)
    items = items[:50]

    nsfw = any(item.nsfw for item in items)

    params = {
        "title": f'{conn.nick} presents: "{text or "random images"}"',
        "ids": ",".join([item.id for item in items]),
        "layout": "blog",
        "account_url": None,
    }
    album = container.api.create_album(params)

    if nsfw:
        return f"[\x02nsfw\x02] https://imgur.com/a/{album['id']}"

    return f"https://imgur.com/a/{album['id']}"
