from __future__ import annotations

import os
import platform
import time
from datetime import timedelta
from typing import TYPE_CHECKING

import cloudbot
from cloudbot import hook
from cloudbot.util.filesize import size as format_bytes

if TYPE_CHECKING:
    from cloudbot.client import Client
    from cloudbot.event_functions import EventMessage, EventReply

try:
    import psutil
except ImportError:
    psutil = None


@hook.command(autohelp=False)
def about(text, conn: Client, bot) -> str:
    """- Gives information about CloudBot. Use .about license for licensing information"""
    if text.lower() in ("license", "gpl", "source"):
        return f"CloudBot Refresh is released under the GPL v3 license, get the source code at {bot.repo_link}"

    return f"{conn.nick} is powered by CloudBot Refresh! ({cloudbot.__version__}) - {bot.repo_link}"


@hook.command(autohelp=False)
def system(reply: EventReply, message: EventMessage) -> None:
    """- Retrieves information about the host system."""

    # Get general system info
    sys_os = platform.platform()
    python_implementation = platform.python_implementation()
    python_version = platform.python_version()
    sys_architecture = "-".join(platform.architecture())
    sys_cpu_count = platform.machine()

    reply(
        f"OS: \x02{sys_os}\x02, "
        f"Python: \x02{python_implementation} {python_version}\x02, "
        f"Architecture: \x02{sys_architecture}\x02 (\x02{sys_cpu_count}\x02)"
    )

    if psutil:
        process = psutil.Process(os.getpid())

        # get the data we need using the Process we got
        cpu_usage = process.cpu_percent(1)
        thread_count = process.num_threads()
        memory_usage = format_bytes(process.memory_info()[0])
        uptime = timedelta(seconds=round(time.time() - process.create_time()))

        message(
            f"Uptime: \x02{uptime}\x02, "
            f"Threads: \x02{thread_count}\x02, "
            f"CPU Usage: \x02{cpu_usage}\x02, "
            f"Memory Usage: \x02{memory_usage}\x02"
        )


@hook.command("sauce", "source", autohelp=False)
def sauce(bot) -> str:
    """- Returns a link to the source"""
    return (
        "Check out my source code! I am a fork of cloudbot: "
        "https://github.com/CloudBotIRC/CloudBot/ and my source is here: "
        f"{bot.repo_link}"
    )
