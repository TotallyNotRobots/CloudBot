import requests

from cloudbot import hook

api_url = "http://api.brewerydb.com/v2/search?format=json"


def api_get(query):
    """Use the RESTful Google Search API"""
    url = 'http://api.brewerydb.com/v2/search?q=%s' \
          '&type=beer'
    return http.get_json(url % query)


@hook.command('brew')
def brew(text, bot):
    """<query> - returns the first brewerydb search result for <query>"""

    api_key = bot.config.get("api_keys", {}).get("brewerydb")
    if not api_key:
        return "No brewerydb API key set."

    params = {'key': api_key, 'type': 'beer', 'withBreweries': 'Y', 'q': text}
    request = requests.get(api_url, params=params)

    if request.status_code != requests.codes.ok:
        return "Failed to fetch info ({})".format(request.status_code)

    response = request.json()
    #print(response)

    output = "No results found."

    try:
        if response['totalResults']:
            beer = response['data'][0]
            brewery = beer['breweries'][0]

            content = {
                name: beer['nameDisplay'],
                style: beer['style']['shortName'],
                abv: beer['abv'],
                brewer: brewery['name'],
                url: brewery['website']
            }

            output = "{} by {} ({}, {}% ABV) - {}".format(*content)
    except Exception as e:
        output = "Error parsing results."

    return output
