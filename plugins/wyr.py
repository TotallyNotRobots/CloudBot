"""
wyr.py

A plugin that uses the RRRather.com API to return random "Would you rather" questions.

Created By:
    - Foxlet <http://furcode.co/>
    - Luke Rogers <https://github.com/lukeroge>

Special Thanks:
    - https://www.rrrather.com/ for adding extra features to their API to make this command possible

License:
    BSD 3-Clause License
"""
from cloudbot import hook


@hook.command("wyr", "wouldyourather", autohelp=False)
def wyr():
    """- What would you rather do? This API has been retired"""
    return "rrrather.com has been retired"
