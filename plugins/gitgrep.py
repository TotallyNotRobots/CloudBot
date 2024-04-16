# Search for code in github: https://grep.app
# Author: Matheus Fillipe
# Date: 02/08/2022

import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from cloudbot import hook
from cloudbot.util.queue import Queue

API = "https://grep.app/api/search"


@dataclass
class Result:
    url: str
    lines: list


results_queue = Queue()


def grep(query: str, **params) -> ([str], [str]):
    res = []
    params = {
        "q": query,
        **params,
    }

    response = requests.get(API, params=params)
    obj = response.json()
    for i in range(len(obj["hits"]["hits"])):
        match = obj["hits"]["hits"][i]
        snippet = match["content"]["snippet"]

        soup = BeautifulSoup(snippet, "html.parser")

        # Find div with class 'lineno'
        lineno = soup.find("div", class_="lineno")
        lineno = lineno.text if lineno else "1"

        url = (
            "https://github.com/"
            + match["repo"]["raw"]
            + "/blob/"
            + match.get("branch", {}).get("raw", "master")
            + "/"
            + match["path"]["raw"]
            + "#L"
            + lineno
        )

        lines = []
        for pre in soup.find_all("tr"):
            pre.find_all("td")[0].decompose()
            lines.append(pre.text)

        res.append(Result(url, lines))

    langs = [
        lang["val"]
        for lang in obj.get("facets", {}).get("lang", {}).get("buckets", [])
    ]

    return res, langs


@hook.command("gitgrepn", "grepn", autohelp=False)
def gitnext(text, reply, chan, nick) -> str:
    """Gets next result in gitgrep."""
    global results_queue
    results = results_queue[chan][nick]
    user = text.strip().split()[0] if text.strip() else ""
    if user:
        if user in results_queue[chan]:
            results = results_queue[chan][user]
        else:
            return f"Nick '{user}' has no queue."

    if len(results) == 0:
        return "No [more] results found."

    r = results.pop()
    for line in [line for line in r.lines[:3] if line.strip()]:
        reply(line)
    reply(f"-->  {r.url}")


@hook.command("gitgrep", "grep")
def gitgrep(text, reply, chan, nick):
    """[args] <query> - Searches for <query> in github using grep.app and returns the first url.
    Optional parameters are: -l <lang>: Language filter (you can use multiple),  -w: Match whole words,
    -i: ignore case, -e: Use regex query
    """
    global results_queue
    params = {}

    def findargs(text):
        text = text.strip()
        match = re.match(r"^-l\s+(\S+)", text)
        start = 0
        if match:
            if "f.lang" not in params:
                params["f.lang"] = []
            params["f.lang"].append(match[1])
            start = match.end()

        if re.search("^-w ", text):
            params["words"] = "true"
            start = 3

        if re.search("^-i ", text):
            params["case"] = "false"
            start = 3

        if re.search("^-e ", text):
            params["regexp"] = "true"
            start = 3

        if start == 0:
            return text
        text = text[start:]
        return findargs(text)

    text = findargs(text)
    if "case" not in params:
        params["case"] = "true"
    else:
        del params["case"]

    if "regexp" in params and "words" in params:
        return "You can't use -w and -e at the same time."

    results, langs = grep(text, **params)

    if len(results) == 0 and "f.lang" in params:
        if len(langs) == 0:
            return "No results found."
        corrected_langs = []
        for lang in langs:
            for plang in params["f.lang"]:
                if lang.casefold() == plang.casefold():
                    corrected_langs.append(lang)

        if len(corrected_langs) == 0:
            return (
                "No results found. Suggested langs for this query: "
                + ", ".join(langs)
            )

        params["f.lang"] = corrected_langs
        results, langs = grep(text, **params)

    results_queue[chan][nick] = results
    results_queue[chan][nick].metadata.langs = langs
    return gitnext("", reply, chan, nick)
