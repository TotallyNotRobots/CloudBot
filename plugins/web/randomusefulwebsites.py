from cloudbot import hook
import requests

url = 'http://randomusefulwebsites.com/jump.php'
headers = {'Referer': 'http://randomusefulwebsites.com'}

@hook.command('randomusefulsite', 'randomwebsite', 'randomsite')
def randomusefulwebsite():
	response = requests.head(url, headers=headers, allow_redirects=True)
	return response.url
