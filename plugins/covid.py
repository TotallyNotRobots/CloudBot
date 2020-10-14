import json
from urllib.request import urlopen

from cloudbot import hook

slugs = []
isos = []


def getglobal():
    api = urlopen("https://api.covid19api.com/world")
    data = json.loads(api.read())
    data = data[0]
    cases = data["TotalConfirmed"]
    deaths = data["TotalDeaths"]
    recovered = data["TotalRecovered"]
    return "Global: Cases: %s Deaths: %s Recovered: %s" % (
        cases,
        deaths,
        recovered,
    )


def getcountry(country):
    api = urlopen("https://api.covid19api.com/live/country/" + country)
    data = json.loads(api.read())
    fullname = data[0]["Country"]
    cases = 0
    deaths = 0
    recovered = 0
    for row in data:
        cases += row["Confirmed"]
        deaths += row["Deaths"]
        recovered += row["Recovered"]
    return "%s: Cases: %s Deaths: %s Recovered: %s" % (
        fullname,
        cases,
        deaths,
        recovered,
    )


@hook.command("covid", autohelp=False)
def covid(text, reply):
    r"""<country> - returns covid numbers"""
    country = text.split(" ")[0]
    if (
        not country in slugs
        and not country.upper() in isos
        and not country == "global"
    ):
        return "Error, %s is not a valid country" % country
    if country == "global":
        response = getglobal()
    else:
        response = getcountry(country)
    return response


@hook.on_connect
def getcountries():
    if len(slugs) > 0 and len(isos) > 0:
        return
    slugs.clear()
    isos.clear()
    api = urlopen("https://api.covid19api.com/countries")
    data = json.loads(api.read())
    for row in data:
        slugs.append(row["Slug"])
        isos.append(row["ISO2"])
