import socket

import requests

from cloudbot import hook

from time import sleep

API = "https://api.funtranslations.com/translate"

LANGS = {
    "morse": f"{API}/morse",
    "morse2english": f"{API}/morse2english ",
    "morseaudio": f"{API}/morse/audio",
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


def tor_check_code(s: socket, failmsg: str):
    c = s.recv(1024).decode().strip().split()[0]
    if str(c) != "250":
        raise Exception(failmsg)


def tor_refresh():
    # Create tcp socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TOR_HOST, TOR_PORT))

    # Get new ip
    s.sendall(f"AUTHENTICATE \"{TOR_PASSWORD}\"\n".encode())
    tor_check_code(s, "Authentication failed")
    s.sendall(b"signal NEWNYM\n")
    tor_check_code(s, "Signal failed")
    s.sendall(b"QUIT\n")
    print(s.recv(2048).decode())
    s.close()


def tor_request_get(*args, **kwargs):
    return requests.get(*args,
                        proxies=dict(http=f'socks5://{TOR_SOCKS5_HOST}:{TOR_SOCKS5_PORT}',
                                     https=f'socks5://{TOR_SOCKS5_HOST}:{TOR_SOCKS5_PORT}'),
                        **kwargs)


def tor_request_post(*args, **kwargs):
    return requests.post(*args,
                         proxies=dict(http=f'socks5://{TOR_SOCKS5_HOST}:{TOR_SOCKS5_PORT}',
                                      https=f'socks5://{TOR_SOCKS5_HOST}:{TOR_SOCKS5_PORT}'),
                         **kwargs)


def upload_file(file, base64: str):
    url = "http://ttm.sh"
    payload = {'file': open(file, "rb")}
    response = requests.request("POST", url, files=payload)
    return response.text.strip()


def torip():
    return tor_request_get("http://ifconfig.me").text.strip()


@hook.command("funtranslate", "tr", autohelp=False)
def funtranslate(text, reply):
    """<target> <text> - Translates <text> using funtranslations.com"""
    if not text:
        return "No text to translate"

    # Get language
    lang = text.split()[0]
    if lang not in LANGS:
        if lang == "list":
            return "Available languages: " + ", ".join(LANGS.keys())
        return "Invalid language, Type .tr list to see available ones"

    # Get text
    text = " ".join(text.split()[1:])

    # Translate
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    data = f'text={text}'

    response = requests.post(LANGS[lang], headers=headers, data=data)

    def process_response(response):
        resp = response.json()
        if "error" not in resp:
            # TODO check for file responses etc
            return resp['contents']['translated']
        raise Exception(str(resp['error']))

    reply("Sorry for the delay, im trying a proxy")
    try:
        return process_response(response)
    except Exception:
        reply(f"Trying with tor proxy: {torip()}")
        attempts = 0
        while attempts < 3:
            response = tor_request_post(LANGS[lang], headers=headers, data=data)
            try:
                return "--> " + process_response(response)
            except Exception:
                attempts += 1
                reply(f"{torip()} trying new tor circuit")
                tor_refresh()

    return "Tried to use tor 3 times, giving up"
