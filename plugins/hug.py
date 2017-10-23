import json
from pathlib import Path

from cloudbot import hook
from cloudbot.util.textgen import TextGenerator

hug_data = {}


@hook.on_start
def load_hug(bot):
    hug_data.clear()
    data_file = Path(bot.data_dir) / "hug.json"
    with data_file.open(encoding='utf-8') as f:
        hug_data.update(json.load(f))


@hook.command("hug")
def hug(text, nick, message):
    """hugs <user>"""
    data = {
        'nick': nick,
        'target': text,
    }

    generator = TextGenerator(hug_data['templates'], hug_data['parts'], variables=data)
    message(generator.generate_string())
