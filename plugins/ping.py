"""
ping.py

Generates fun names using the textgen module.

Created By:
    - Bjorn Neergaard <https://github.com/neersighted>

Modified By:
    - Luke Rogers <https://github.com/lukeroge>

License:
    GPL v3
"""

import os
import re
import subprocess

from cloudbot import hook

unix_ping_regex = re.compile(r"(\d+.\d+)/(\d+.\d+)/(\d+.\d+)/(\d+.\d+)")
win_ping_regex = re.compile(
    r"Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms"
)

IS_WINDOWS = os.name == "nt"


@hook.command()
def ping(text, reply):
    """<host> [count] - pings <host> [count] times"""

    args = text.split(" ")
    host = args[0]

    # check for a second argument and set the ping count
    if len(args) > 1:
        count = int(args[1])
        if count > 20:
            count = 20
    else:
        count = 5

    if IS_WINDOWS:
        args = ["ping", "-n", str(count), host]
    else:
        args = ["ping", "-c", str(count), host]

    reply("Attempting to ping {} {} times...".format(host, count))
    try:
        pingcmd = subprocess.check_output(args).decode("utf-8")
    except subprocess.CalledProcessError:
        return "Could not ping host."

    if re.search("(?:not find host|timed out|unknown host)", pingcmd, re.I):
        return "Could not ping host."

    if IS_WINDOWS:
        m = re.search(win_ping_regex, pingcmd)
        r = int(m.group(2)) - int(m.group(1))
        return "min: %sms, max: %sms, average: %sms, range: %sms, count: %s" % (
            m.group(1),
            m.group(2),
            m.group(3),
            r,
            count,
        )

    m = re.search(unix_ping_regex, pingcmd)
    return "min: %sms, max: %sms, average: %sms, range: %sms, count: %s" % (
        m.group(1),
        m.group(3),
        m.group(2),
        m.group(4),
        count,
    )
