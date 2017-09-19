"""
All GIFs courtesy of http://bestanimations.com/
"""
import random
from urllib.parse import urljoin

from cloudbot import hook
from cloudbot.util.http import get_soup

BASE_URL = "http://bestanimations.com/Animals/Mammals/Dogs/"
DOG_PAGES = (
    "Dogs.html",
    "Dogs2.html",  # Pugs
    "Dogs3.html",  # Puppies
)


def get_gifs(url):
    soup = get_soup(url)
    container = soup.find('div', class_="row")
    gifs = [urljoin(url, elem["src"]) for elem in container.find_all('img')]
    return gifs


def get_random_gif(url):
    return random.choice(get_gifs(url))


@hook.command(autohelp=False)
def doggifs(logger):
    """- Returns a random dog GIF from http://bestanimations.com/"""
    page = random.choice(DOG_PAGES)
    url = urljoin(BASE_URL, page)
    try:
        return get_random_gif(url)
    except Exception:
        logger.exception("An error occurred while trying to get a dog GIF:")
        return "Error occurred when retrieving GIF"
