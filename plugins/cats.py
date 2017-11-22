import requests
from cloudbot import hook


@hook.command(autohelp=False)
def cats(reply):
    """gets a fucking fact about cats."""

    attempts = 0
    while True:
        try:
            r = requests.get(
                'http://catfacts-api.appspot.com/api/facts?number=1')
        except Exception:
            if attempts > 2:
                reply("There was an error contacting the API.")
                raise
            else:
                attempts += 1
                continue
        json = r.json()
        response = json['facts']
        return response

@hook.command(autohelp=False)
def catgifs(reply):
    """gets a fucking cat gif."""
    attempts = 0
    while True:
        try:
            r = requests.get("http://marume.herokuapp.com/random.gif")
        except Exception:
            if attempts > 2:
                reply("there was an error finding a cat gif for you.")
                raise
            else:
                attempts += 1
                continue
        response = r.url
        return "OMG A CAT GIF: {}".format(response)
