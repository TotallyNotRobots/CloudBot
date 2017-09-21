import codecs
import json
import os
import re
from collections import namedtuple, defaultdict

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
    BasicFood("donut", "donut", "donut.json", "a donut"),
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
    # Kept for posterity
    # <Luke> Hey guys, any good ideas for plugins?
    # <User> I don't know, something that lists every potato known to man?
    # <Luke> BRILLIANT
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


def basic_format(text, data, **kwargs):
    user = text
    kwargs['user'] = user

    generator = textgen.TextGenerator(
        data["templates"], data["parts"], variables=kwargs
    )

    return generator.generate_string()


def make_cmd_list(value):
    if isinstance(value, str):
        value = [value]
    return value


def basic_food(food):
    def func(text, action):
        if not is_valid(text):
            return "I can't give {} to that user.".format(food.unitname)

        action(basic_format(text, basic_food_data[food.name]))

    func.__name__ = food.name
    func.__doc__ = "<user> - gives {} to [user]".format(food.unitname)
    return func


for food in BASIC_FOOD:
    globals()[food.name] = hook.command(*make_cmd_list(food.commands))(basic_food(food))

