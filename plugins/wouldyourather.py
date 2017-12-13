from cloudbot import hook
from cloudbot.util import http


@hook.command("wouldyou", autohelp=False)
def wouldyourather_first(reply):
    """- Asks a would you rather question"""

    attempts = 0
    while True:
        try:
            json = http.get_json('http://rrrather.com/botapi')
        except Exception:
            if attempts > 2:
                reply("There was an error contacting the rrrather.com API.")
                raise
            else:
                attempts += 1
                continue
        response = "{}: {} \x02OR\x0F {}?".format(json['title'], json['choicea'], json['choiceb'])
        return response
