"""Maybe more godot relatd stuff in the future."""
# Depents on htmlq: cargo install htmlq
from cloudbot import hook
import datetime
import re
import subprocess

@hook.command(autohelp=False)
def jamdate(reply):
    """- Next godot jam date"""
    # TODO scrape like a real person would, using bs4 and requests
    text = subprocess.check_output("curl -s \"$(curl -s https://godotwildjam.com | htmlq \"a.elementor-button-link\" --attribute href | head -1)\" | htmlq --text \".date_data\"", shell=True).decode().strip()
    reply(text)
    from_date = re.search(r'(?<= from )(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', text).group(1)
    to_date = re.search(r'(?<= to )(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', text).group(1)
    from_date = datetime.datetime.strptime(from_date, "%Y-%m-%d %H:%M:%S")
    to_date = datetime.datetime.strptime(to_date, "%Y-%m-%d %H:%M:%S")
    start_time_left = (from_date - datetime.datetime.utcnow())
    end_time_left = (to_date - datetime.datetime.utcnow())

    reply(f"Jam starts in {start_time_left.days} days {start_time_left.seconds//3600} hours {(start_time_left.seconds//60)%60} minutes.")
    reply(f"Jam ends in {end_time_left.days} days {end_time_left.seconds//3600} hours {(end_time_left.seconds//60)%60} minutes.")
