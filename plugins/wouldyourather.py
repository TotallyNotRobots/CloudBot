from cloudbot import hook
from cloudbot.util import http


@hook.command("wouldyou", autohelp=False)
def wouldyourather_first(reply):
    """- Asks a would you rather question"""

    try:
        json = http.get_json('http://rrrather.com/botapi')
    except Exception:
        reply("There was an error contacting the rrrather.com API.")
        raise

    response = "{}: {} \x02OR\x0F {}?".format(json['title'], json['choicea'], json['choiceb'])
    return response
