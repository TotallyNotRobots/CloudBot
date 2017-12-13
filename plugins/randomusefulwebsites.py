import requests

from cloudbot import hook

url = 'http://www.discuvver.com/jump2.php'
headers = {'Referer': 'http://www.discuvver.com'}


@hook.command('randomusefulsite', 'randomwebsite', 'randomsite', 'discuvver')
def randomusefulwebsite():
    response = requests.head(url, headers=headers, allow_redirects=True)
    response.raise_for_status()
    return response.url
