"""wrapper for https://github.com/matheusfillipe/speech-api."""

import json
import os
import subprocess
import tempfile
import urllib.parse
from pprint import pformat

import requests
import validators

from cloudbot import hook
from cloudbot.bot import bot

API = bot.config["plugins"]["speech"]["api"]
headers = {"Authorization": "Bearer " + bot.config.get_api_key("speech", "")}


def stt_file(file, language):
    url = f"{API}stt/{language}"
    payload = {"file": open(file, "rb")}
    response = requests.request("POST", url, files=payload, headers=headers)
    return response.json()


def stt_url(url, language):
    url = f"{API}stt/{language}?url=" + urllib.parse.quote(url)
    response = requests.request("POST", url, headers=headers)
    return response.json()


def langs():
    url = f"{API}stt/languages"
    response = requests.request("GET", url, headers=headers)
    return response.json()


def pastebin(text):
    url = "http://ix.io"
    payload = {"f:1=<-": text}
    response = requests.request("POST", url, data=payload)
    return response.text


def upload_file(file):
    url = "https://ttm.sh"
    payload = {"file": open(file, "rb")}
    response = requests.request("POST", url, files=payload)
    return response.text.strip()


def targs(text):
    return text.strip().split()


@hook.command()
def sttlangs():
    return str(langs())


def stt(text, bot, nick, use_json=False):
    """[language] <url> - Transcribe audio from url into text. Language defaults to english. Use .sttlangs or .stt langs to see available languages."""
    args = targs(text)
    if not args:
        return "I need at least one url argument"
    languages = langs()
    if args[0] in languages:
        language = args[0]
        url = args[1]
    elif args[0] in ["langs", "languages"]:
        return str(languages)
    elif validators.url(args[0]):
        url = args[0]
        language = "english"
    else:
        return "I need a valid url to work with"
    result = stt_url(url, language)
    if "error" in result:
        return f"error: {result['error']}"
    if use_json:
        return pastebin(pformat(json.dumps(result), 4))
    text = result["full"]
    if len(text) > 450:
        return pastebin(text)
    return text


@hook.command("stt", autohelp=False)
def stt_simple(text, bot, nick):
    return stt(text, bot, nick)


@hook.command("sttjson", autohelp=False)
def stt_json(text, bot, nick):
    return stt(text, bot, nick, use_json=True)


def langs2():
    url = f"{API}tts/languages"
    response = requests.request("GET", url, headers=headers)
    return response.json()


@hook.command("ttslangs")
def ttslangs():
    return str(langs2())


@hook.command("tts", autohelp=False)
def speak(text, bot, nick):
    """[language] <text> - Speech to text. If no language is specified use en. List languaes with .ttslangs."""
    args = targs(text)
    if not args:
        return "I need at least one text argument"
    languages = langs2()
    if args[0] in languages:
        language = args[0]
        sentence = " ".join(args[1:])
    else:
        sentence = text
        language = "en"

    filename = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
    url = f"{API}tts/{language}"
    payload = {"text": sentence}

    with requests.request(
        "POST", url, data=payload, headers=headers, stream=True
    ) as r:
        r.raise_for_status()
        if (
            r.headers.get("content-type") == "application/json"
            and "error" in r.json()
        ):
            os.remove(filename)
            return f"error: {r.json()['error']}"
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    mp3_filename = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    try:
        subprocess.call(
            ["ffmpeg", "-y", "-i", filename, "-f", "mp3", mp3_filename]
        )
        url = upload_file(mp3_filename)
    except Exception:
        url = upload_file(filename)

    try:
        os.remove(filename)
        os.remove(mp3_filename)
    except Exception:
        pass

    return url
