import json
import random
from pathlib import Path

from cloudbot import hook
from cloudbot.util.textgen import TextGenerator

fight_data = {}


@hook.on_start
def load_data(bot):
    fight_data.clear()
    data_file = Path(bot.data_dir) / "fight.json"
    with data_file.open(encoding='utf-8') as f:
        fight_data.update(json.load(f))


@hook.command("fight", "fite", "spar", "challenge")
def fight(text, nick, message):
    """<nick>, makes you fight <nick> and generates a winner."""
    data = {
        'user1': nick,
        'user2': text,
    }

    generator = TextGenerator(fight_data['templates'], fight_data['parts'], variables=data)
    message(generator.generate_string())
