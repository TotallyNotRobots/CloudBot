# Search for code in github: https://grep.app
# Author: Matheus Fillipe
# Date: 02/08/2022

from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from cloudbot import hook

API = 'https://grep.app/api/search'


@dataclass
class Result:
    url: str
    lines: list


results = []


def grep(query: str) -> str:
    global results
    results = []

    params = {
        'q': query,
    }

    response = requests.get(API, params=params)
    obj = response.json()
    for i in range(len(obj['hits']['hits'])):
        match = obj['hits']['hits'][i]
        snippet = match['content']['snippet']

        soup = BeautifulSoup(snippet, 'html.parser')

        # Find div with class 'lineno'
        lineno = soup.find('div', class_='lineno')
        lineno = lineno.text if lineno else "1"

        url = "https://github.com/" + \
            match['repo']['raw'] + "/blob/" + \
            match.get('branch', {}).get('raw', 'master') + "/" + match['path']['raw'] + \
            "#L" + lineno

        lines = []
        for pre in soup.find_all('tr'):
            pre.find_all('td')[0].decompose()
            lines.append(pre.text)

        results.append(Result(url, lines))


@hook.command("gitgrepn", "grepn", autohelp=False)
def gitnext(reply) -> str:
    """Gets next result in gitgrep."""
    global results
    if len(results) == 0:
        return "No [more] results found."
    r = results.pop(0)
    for line in r.lines[:3]:
        reply(line)
    reply(f"-->  {r.url}")


@hook.command("gitgrep", "grep")
def gitgrep(text, reply):
    """gitgrep <query> - Searches for <query> in github using grep.app and returns the first url"""
    grep(text)
    return gitnext(reply)
