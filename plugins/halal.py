# halaal for gonzobot
import json
from pathlib import Path

from cloudbot import hook
from cloudbot.util.textgen import TextGenerator

halal_data = {}
kosher_data = {}


def load_data(bot):
    def load_file(file, data_dict):
        data_dict.clear()
        path = Path(bot.data_dir) / file
        with path.open(encoding='utf-8') as f:
            data_dict.update(json.load(f))

    load_file("halal.json", halal_data)
    load_file("kosher.json", kosher_data)


@hook.command('halaal', 'halal', autohelp=False)
def serving(text, action):
    """Serves halaal dishes to some one in the channel"""
    data = {}
    if text:
        templates = halal_data['target_templates']
        data['target'] = text
    else:
        templates = halal_data['templates']

    generator = TextGenerator(templates, halal_data['parts'], variables=data)
    action(generator.generate_string())


@hook.command('kosher', autohelp=False)
def kserving(text, action):
    """Servers a Kosher dish to some one in the channel. Part of halal.py. Made with help of snoonet user Yat"""
    data = {}
    if text:
        templates = kosher_data['target_templates']
        data['target'] = text
    else:
        templates = kosher_data['templates']

    generator = TextGenerator(templates, kosher_data['parts'], variables=data)
    action(generator.generate_string())

# written by ilgnome
# find me in #gonzobot
