import io
import socket
from base64 import b64decode

import requests

from cloudbot import hook
from cloudbot.bot import bot

API = "https://api.funtranslations.com/translate"

LANGS = {
    "morse": f"{API}/morse",
    "morse2english": f"{API}/morse2english ",
    "morse2audio": f"{API}/morse/audio",
    "valspeak": f"{API}/valspeak",
    "jive": f"{API}/jive",
    "cockney": f"{API}/cockney",
    "brooklyn": f"{API}/brooklyn",
    "ermahgerd": f"{API}/ermahgerd",
    "pirate": f"{API}/pirate",
    "minion": f"{API}/minion",
    "ferblatin": f"{API}/ferblatin",
    "chef": f"{API}/chef",
    "dolan": f"{API}/dolan",
    "fudd": f"{API}/fudd",
    "braille": f"{API}/braille/unicode",
    "sindarin": f"{API}/sindarin",
    "quneya": f"{API}/quneya",
    "oldenglish": f"{API}/oldenglish",
    "shakespeare": f"{API}/shakespeare",
    "us2uk": f"{API}/us2uk",
    "uk2us": f"{API}/uk2us",
    "vulcan": f"{API}/vulcan",
    "klingon": f"{API}/klingon",
    "yoda": f"{API}/yoda",
    "sith": f"{API}/sith",
    "cheunh": f"{API}/cheunh",
    "gugan": f"{API}/gugan",
    "piglatin": f"{API}/piglatin",
    "mandalorian": f"{API}/mandalorian",
    "huttese": f"{API}/huttese",
}


# Changes tor ip using tcp IPC
# Tor proxy
TOR_SOCKS5_HOST = "127.0.0.1"
TOR_SOCKS5_PORT = 9050
# Control info for tor
TOR_HOST = "127.0.0.1"
TOR_PORT = 9051
TOR_PASSWORD = ""


last_proxy = None


def tor_check_code(s: socket, failmsg: str):
    c = s.recv(1024).decode().strip().split()[0]
    if str(c) != "250":
        raise Exception(failmsg)


def upload_file(file):
    url = "https://ttm.sh"
    payload = {"file": file}
    response = requests.request("POST", url, files=payload)
    return response.text.strip()


def tor_refresh():
    # Create tcp socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TOR_HOST, TOR_PORT))

    # Get new ip
    s.sendall(f'AUTHENTICATE "{TOR_PASSWORD}"\n'.encode())
    tor_check_code(s, "Authentication failed")
    s.sendall(b"signal NEWNYM\n")
    tor_check_code(s, "Signal failed")
    s.sendall(b"QUIT\n")
    print(s.recv(2048).decode())
    s.close()


def tor_request_get(*args, **kwargs):
    return requests.get(
        *args,
        proxies=dict(
            http=f"socks5://{TOR_SOCKS5_HOST}:{TOR_SOCKS5_PORT}",
            https=f"socks5://{TOR_SOCKS5_HOST}:{TOR_SOCKS5_PORT}",
        ),
        **kwargs,
    )


def tor_request_post(*args, **kwargs):
    return requests.post(
        *args,
        proxies=dict(
            http=f"socks5://{TOR_SOCKS5_HOST}:{TOR_SOCKS5_PORT}",
            https=f"socks5://{TOR_SOCKS5_HOST}:{TOR_SOCKS5_PORT}",
        ),
        **kwargs,
    )


def proxy_request_post(proxies, *args, **kwargs):
    return requests.post(*args, proxies=proxies, **kwargs)


def torip():
    return tor_request_get("http://ifconfig.me").text.strip()


@hook.command("funtranslate", "tr", autohelp=False)
def funtranslate(text, reply):
    """<target> <text> - Translates <text> using funtranslations.com"""
    global last_proxy
    if not text:
        return "No text to translate"

    # Get language
    lang = text.split()[0]
    if lang not in LANGS:
        if lang == "list":
            return "Available languages: " + ", ".join(LANGS.keys())
        return "Invalid language, Type '.tr list' to see available ones"

    # Get text
    text = " ".join(text.split()[1:])

    # Translate
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = f"text={text}"

    response = requests.post(LANGS[lang], headers=headers, data=data)

    def process_response(response):
        resp = response.json()
        if "error" not in resp:
            translated = resp.get("contents", {}).get("translated")
            if isinstance(translated, str):
                return translated
            if isinstance(translated, dict):
                if "audio" in translated:
                    b64 = translated["audio"]
                    b64audio = b64.split(",")[-1]
                    wave_bytes = b64decode(b64audio)
                    file = io.BytesIO(wave_bytes)
                    return upload_file(file)
            if isinstance(translated, list):
                return " ".join(translated)
            return "Not implemented"

    output = process_response(response)
    if output:
        return output

    if last_proxy is not None:
        try:
            response = proxy_request_post(
                last_proxy, LANGS[lang], headers=headers, data=data
            )
            output = process_response(response)
            if output:
                return "p: " + output

        except requests.exceptions.ProxyError:
            pass

    webshare_key = bot.config.get_api_key("webshare")
    if webshare_key:

        def mkuri(proxy):
            addr = proxy["proxy_address"]
            port = proxy["ports"]["http"]
            username = proxy["username"]
            password = proxy["password"]
            return f"http://{username}:{password}@{addr}:{port}"

        response = requests.get(
            "https://proxy.webshare.io/api/proxy/list/?page=1",
            headers={"Authorization": "Token " + webshare_key},
        )
        r = response.json().get("results")
        if r:
            proxies = [
                {"http": mkuri(proxy), "https": mkuri(proxy)} for proxy in r
            ]
            i = 0
            while i < len(proxies):
                i += 1
                if last_proxy in proxies:
                    last_proxy = proxies[
                        (proxies.index(last_proxy) + 1) % len(proxies)
                    ]
                else:
                    last_proxy = proxies[0]

                try:
                    response = proxy_request_post(
                        last_proxy, LANGS[lang], headers=headers, data=data
                    )
                except requests.exceptions.ProxyError:
                    continue

                output = process_response(response)
                if output:
                    return "p: " + output

        attempts = 0
        while attempts < 3:
            response = tor_request_post(LANGS[lang], headers=headers, data=data)
            output = process_response(response)
            if output:
                return "t: " + output
            attempts += 1
            tor_refresh()

    return "Tried to use proxies and tor 3 times, giving up"
