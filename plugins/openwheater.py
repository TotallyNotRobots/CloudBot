import os

from pyweather import curweath

from cloudbot import hook
from cloudbot.bot import bot

api_key = bot.config.get_api_key("openwheater")
os.environ["API_KEY"] = api_key


@hook.command("we")
def weater(text):
    x = curweath.by_cname(text)
    if "message" in x:
        return x["message"]
    return f"{x.name} (Country: {x.sys.country}, Coord: {x.coord.lon}, {x.coord.lat}) -- {x.weather[0].description} {round(x.main.temp-273.15) }Cº min {round(x.main.temp_min-273.15)}Cº max {round(x.main.temp_max-273.15)}Cº sensation {round(x.main.feels_like-273.15)}Cº humidity {x.main.humidity}%"
