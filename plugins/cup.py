from datetime import datetime, timedelta
from cloudbot import hook
from cloudbot.bot import bot

import requests

API = "http://api.cup2022.ir/api/v1/{}"


def get(url, bearer):
    response = requests.get(url, headers={"Authorization": "Bearer " + bearer, "Content-Type": "application/json"})
    try:
        return response.json()
    except:
        raise Exception(response.text)


def get_token(email, password):
    json_data = {
        'email': email,
        'password': password,
    }

    response = requests.post('http://api.cup2022.ir/api/v1/user/login', json=json_data)
    try:
        return response.json()['data']['token']
    except:
        raise Exception(response.text)


@hook.command("cup", autohelp=False)
def cup(text):
    """"<n> number of days window"""

    try:
        days = float(text) if text else 1
    except ValueError:
        return "Invalid number of days. Can be integer or float"

    email = bot.config.get_api_key("cup_api_email")
    password = bot.config.get_api_key("cup_api_password")
    try:
        api = get_token(email, password)
        matches = get(API.format("match"), api)['data']
    except Exception as e:
        return "Error: {}".format(e)
    matches_result = []
    # sort matches by date
    dateformat = "%m/%d/%Y %H:%M"
    matches = sorted(matches, key=lambda k: datetime.strptime(
        k['local_date'], dateformat))
    for match in matches:
        # only get matches that are in 2 days range
        date = datetime.strptime(match["local_date"], dateformat)
        delta = timedelta(days=days)
        now = datetime.now()
        if date > now + delta or date < now - delta:
            continue
        prepend = ""
        append = ''
        if match["time_elapsed"] == "notstarted":
            prepend = "🏟  "
        elif match["time_elapsed"] == "finished":
            prepend = "✔️  "
        else:
            prepend = "⚽️ "
            append = f'  time: {match["time_elapsed"]}'

        matches_result.append(
            f'{prepend}{match["local_date"]}  {match["home_team_en"]} vs {match["away_team_en"]}    score: {match["home_score"]} - {match["away_score"]}{append}')

    return ["Legend: 🏟 future game, ⚽️ live game, 🏁 finished gae -times: h1 | hf | h2 "] + matches_result
