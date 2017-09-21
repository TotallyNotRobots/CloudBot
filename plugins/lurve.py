import json
from pathlib import Path

from cloudbot import hook
from cloudbot.util.textgen import TextGenerator

love_data = {}


@hook.on_start
def load_love(bot):
    love_data.clear()
    data_file = Path(bot.data_dir) / "lurve.json"
    with data_file.open(encoding='utf-8') as f:
        love_data.update(json.load(f))


@hook.command("lurve", "luff", "luv")
def lurve(text, nick, message):
    """lurves all over <user>"""
    data = {
        'nick': nick,
        'target': text,
    }

    generator = TextGenerator(love_data['templates'], love_data['parts'], variables=data)
    message(generator.generate_string())
