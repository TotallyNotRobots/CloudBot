import re
import asyncio
import socket
import logging
import requests

from cloudbot import hook

URL = "https://json.geoiplookup.io/{}"

@hook.command
def geoip(text, loop, reply):
    """<host|ip> - Looks up the physical location of <host|ip> using Maxmind GeoLite """
    if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", text):
        ip = text
    else:
        try:
            ip = socket.gethostbyname(text)
        except socket.gaierror:
            return "Invalid input."

    response = requests.get(URL.format(ip))
    if not response.ok:
        return "Error: {}".format(response.status_code)

    data = response.json()

    return "{ip} - {hostname}: \x02Country:\x02 {country_name} ({country_code}), \x02Region:\x02 {region}, \x02District:\x02 {district}, \x02City:\x02 {city}, \x02ISP:\x02 {isp}".format(**data)
