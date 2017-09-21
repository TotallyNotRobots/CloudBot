import json
from pathlib import Path

from cloudbot import hook
from cloudbot.util.textgen import TextGenerator

high_five_data = {}


@hook.on_start
def load_data(bot):
    high_five_data.clear()
    data_file = Path(bot.data_dir) / "highfive.json"
    with data_file.open(encoding='utf-8') as f:
        high_five_data.update(json.load(f))


@hook.command("high5", "hi5", "highfive")
def highfive(nick, text, message):
    """Highfives the requested user"""
    data = {'user': nick, 'nick': text}
    generator = TextGenerator(high_five_data['templates'], high_five_data['parts'], variables=data)
    message(generator.generate_string())
