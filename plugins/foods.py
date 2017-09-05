import asyncio
import codecs
import json
import os
import re
from collections import namedtuple, defaultdict
from itertools import chain

from cloudbot import hook
from cloudbot.util import textgen

nick_re = re.compile("^[A-Za-z0-9_|.\-\]\[\{\}\*\`]*$", re.I)

BasicFood = namedtuple('BasicFood', "name commands datafile unitname")

BASIC_FOOD = (
    BasicFood("sandwich", "sandwich", "sandwich.json", "a potato"),
    BasicFood("taco", "taco", "taco.json", "a taco"),
    BasicFood("coffee", "coffee", "coffee.json", "coffee"),
    BasicFood("noodles", "noodles", "noodles.json", "noodles"),
    BasicFood("muffin", "muffin", "muffin.json", "a muffin"),
    BasicFood("scone", "scone", "scone.json", "a scone"),
    BasicFood("rice", "rice", "rice.json", "rice"),
    BasicFood("tea", "tea", "tea.json", "tea"),
    BasicFood("keto", "keto", "keto.json", "food"),
    BasicFood("beer", "beer", "beer.json", "beer"),
    BasicFood("cheese", "cheese", "cheese.json", "cheese"),
    BasicFood("pancake", "pancake", "pancake.json", "pancakes"),
    BasicFood("chicken", "chicken", "chicken.json", "chicken"),
    BasicFood("nugget", "nugget", "nugget.json", "nuggets"),
    BasicFood("pie", "pie", "pie.json", "pie"),
    BasicFood("brekkie", ["brekkie", "brekky"], "brekkie.json", "brekkie"),
    BasicFood("icecream", "icecream", "icecream.json", "icecream"),
    BasicFood("doobie", "doobie", "doobie.json", "a doobie"),
    BasicFood("pizza", "pizza", "pizza.json", "pizza"),
    BasicFood("chocolate", "chocolate", "chocolate.json", "chocolate"),
    BasicFood("pasta", "pasta", "pasta.json", "pasta"),
    BasicFood("cereal", "cereal", "cereal.json", "cereal"),
    BasicFood("sushi", "sushi", "sushi.json", "sushi"),
    BasicFood("steak", "steak", "steak.json", "a nice steak dinner"),
    BasicFood("milkshake", "milkshake", "milkshake.json", "a milkshake"),
    BasicFood("kebab", "kebab", "kebab.json", "a kebab"),
    BasicFood("cake", "cake", "cake.json", "a cake"),
    BasicFood("potato", "potato", "potato.json", "a potato"),
    BasicFood("cookie", "cookie", "cookies.json", "a cookie"),
)

basic_food_data = defaultdict(dict)


def is_valid(target):
    """ Checks if a string is a valid IRC nick. """
    if nick_re.match(target):
        return True
    else:
        return False


def load_template_data(bot, filename, data_dict):
    data_dict.clear()
    food_dir = os.path.join(bot.data_dir, "food")
    with codecs.open(os.path.join(food_dir, filename), encoding="utf-8") as f:
        data_dict.update(json.load(f))


@hook.on_start()
def load_foods(bot):
    """
    :type bot: cloudbot.bot.CloudBot
    """
    basic_food_data.clear()

    for food in BASIC_FOOD:
        load_template_data(bot, food.datafile, basic_food_data[food.name])


def basic_format(text, data, food_type, **kwargs):
    user = text
    kwargs['user'] = user

    if not is_valid(user):
        return "I can't give {} to that user.".format(food_type)

    generator = textgen.TextGenerator(
        data["templates"], data["parts"], variables=kwargs
    )

    return generator.generate_string()


def make_cmd_list(value):
    if isinstance(value, str):
        value = [value]
    return value


@asyncio.coroutine
@hook.command(*chain.from_iterable(make_cmd_list(food.commands) for food in BASIC_FOOD))
def basic_food(text, triggered_command, action):
    # Find the first food in BASIC_FOOD that matches the triggered command
    for food in BASIC_FOOD:
        cmd_list = make_cmd_list(food.commands)
        if triggered_command in cmd_list or any(cmd.startswith(triggered_command) for cmd in cmd_list):
            break
    else:
        # The triggered command didn't match any loaded foods, WTF!?!?
        return "{} matched an unknown food in foods.py. Congrats! You found a bug! " \
               "Please report this right away.".format(triggered_command)
    action(basic_format(text, basic_food_data[food.name], food.unitname))
