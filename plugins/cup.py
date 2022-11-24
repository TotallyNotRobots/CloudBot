from datetime import datetime, timedelta
from cloudbot import hook
from cloudbot.bot import bot

import requests

API = "http://api.cup2022.ir/api/v1/{}"

def get(url, bearer):
    return requests.get(url, headers={"Authorization": "Bearer " + bearer, "Content-Type": "application/json"}).json()

@hook.command("cup")
def cup(text):
    api = bot.config.get_api_key("cup_api")
    matches = get(API.format("match"), api)['data']
    matches_result = []
    # sort matches by date
    dateformat = "%m/%d/%Y %H:%M"
    matches = sorted(matches, key=lambda k: datetime.strptime(k['local_date'], dateformat))
    for match in matches:
        # only get matches that are in 2 days range
        date = datetime.strptime(match["local_date"], dateformat)
        delta = timedelta(days=2)
        now = datetime.now()
        if date > now + delta or date < now - delta:
            continue
        prepend = ""
        append = ''
        if match["time_elapsed"] not in ["notstarted", "finished"]:
            prepend = "⚽️ "
            append = f'  time: {match["time_elapsed"]}'

        matches_result.append(f'{prepend}{match["local_date"]}  {match["home_team_en"]} vs {match["away_team_en"]}    score: {match["home_score"]} - {match["away_score"]}{append}')

    return matches_result
