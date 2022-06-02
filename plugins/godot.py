"""Maybe more godot relatd stuff in the future."""

import datetime
import urllib.parse

from gazpacho import Soup, get

from cloudbot import hook


@hook.command(autohelp=False)
def jamdate(reply):
    """- Next godot jam date"""
    url_soup = Soup(get("https://godotwildjam.com"))
    url = url_soup.find("a", {"class": "elementor-button-link"})[0].attrs['href']
    soup = Soup(get(url))
    elm = soup.find("div", {"class": "date_data"})
    text = elm.text
    from_date = elm.find("span")[0].text
    to_date = elm.find("span")[1].text
    reply(f"Ich.io Godot {text} from {from_date} to {to_date}")
    from_date = datetime.datetime.strptime(from_date, "%Y-%m-%d %H:%M:%S")
    to_date = datetime.datetime.strptime(to_date, "%Y-%m-%d %H:%M:%S")
    start_time_left = (from_date - datetime.datetime.utcnow())
    end_time_left = (to_date - datetime.datetime.utcnow())

    reply(f"Jam starts in {start_time_left.days} days {start_time_left.seconds//3600} hours {(start_time_left.seconds//60)%60} minutes.")
    reply(f"Jam ends in {end_time_left.days} days {end_time_left.seconds//3600} hours {(end_time_left.seconds//60)%60} minutes.")


@hook.command()
def godocs(text, reply):
    """<text> - Searches on godot documentation"""
    # url encode
    query = urllib.parse.quote(text)
    url = f"https://docs.godotengine.org/_/api/v2/search/?q={query}&project=godot&version=stable&language=en"
    data = get(url)

    i = 0
    used = set()
    for item in data['results']:
        if i == 4:
            break
        description = ""
        for block in item['blocks']:
            if block['type'] == 'section':
                if block['content']:
                    limit = 128
                    description += block['content'][:limit]
                    if len(description) > limit:
                        description += "..."
                break

        if item['path'] in used:
            continue

        i += 1
        used.add(item['path'])
        reply(f"{item['title']}: {description} - {item['domain'] + item['path']}")
