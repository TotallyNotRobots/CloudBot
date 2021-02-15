import json
from collections import defaultdict
from typing import Any, Dict

from cloudbot import hook
from cloudbot.util import textgen


class BasicFood:
    def __init__(self, name, unit, *commands, file=None):
        self.name = name
        self.unit = unit
        self.commands = commands or (name,)
        self.file = file or "{}.json".format(self.name)


BASIC_FOOD = (
    BasicFood("sandwich", "a sandwich"),
    BasicFood("taco", "a taco"),
    BasicFood("coffee", "coffee"),
    BasicFood("noodles", "noodles"),
    BasicFood("muffin", "a muffin"),
    BasicFood("scone", "a scone"),
    BasicFood("donut", "a donut"),
    BasicFood("rice", "rice"),
    BasicFood("tea", "tea"),
    BasicFood("keto", "food"),
    BasicFood("beer", "beer"),
    BasicFood("cheese", "cheese"),
    BasicFood("pancake", "pancakes"),
    BasicFood("chicken", "chicken"),
    BasicFood("nugget", "nuggets"),
    BasicFood("pie", "pie"),
    BasicFood("brekkie", "brekkie", "brekkie", "brekky"),
    BasicFood("icecream", "icecream"),
    BasicFood("doobie", "a doobie"),
    BasicFood("wine", "wine"),
    BasicFood("pizza", "pizza"),
    BasicFood("vpizza", "pizza"),
    BasicFood("chocolate", "chocolate"),
    BasicFood("pasta", "pasta"),
    BasicFood("cereal", "cereal"),
    BasicFood("sushi", "sushi"),
    BasicFood("steak", "a nice steak dinner"),
    BasicFood("burger", "a tasty burger"),
    BasicFood("milkshake", "a milkshake"),
    BasicFood("kebab", "a kebab"),
    BasicFood("cake", "a cake"),
    BasicFood("hotchoc", "hotchoc"),
    BasicFood("squid", "some squid"),
    # Kept for posterity
    # <Luke> Hey guys, any good ideas for plugins?
    # <User> I don't know, something that lists every potato known to man?
    # <Luke> BRILLIANT
    BasicFood("potato", "a potato"),
    BasicFood("cookie", "a cookie", file="cookies.json"),
    BasicFood("soup", "Some Soup"),
    BasicFood("halal", "food", "halal", "halaal"),
    BasicFood("kosher", "food"),
    BasicFood("birthday", "birthday cake"),
)

basic_food_data: Dict[str, Dict[str, Any]] = defaultdict(dict)


def load_template_data(bot, filename, data_dict):
    data_dict.clear()
    food_dir = bot.data_path / "food"
    with open((food_dir / filename), encoding="utf-8") as f:
        data_dict.update(json.load(f))


@hook.on_start()
def load_foods(bot):
    basic_food_data.clear()

    for food in BASIC_FOOD:
        load_template_data(bot, food.file, basic_food_data[food.name])


def basic_format(nick, text, data, **kwargs):
    user = text
    kwargs["user"] = user
    kwargs["target"] = user
    kwargs["nick"] = nick

    if text:
        try:
            templates = data["target_templates"]
        except KeyError:
            templates = data["templates"]
    else:
        templates = data["templates"]

    generator = textgen.TextGenerator(
        templates, data.get("parts", {}), variables=kwargs
    )

    return generator.generate_string()


def basic_food(food):
    def func(text, nick, action, is_nick_valid):
        if not is_nick_valid(text):
            return "I can't give {} to that user.".format(food.unit)

        action(basic_format(nick, text, basic_food_data[food.name]))
        return None

    func.__name__ = food.name
    func.__doc__ = "<user> - gives {} to [user]".format(food.unit)
    return func


def init_hooks():
    for food in BASIC_FOOD:
        globals()[food.name] = hook.command(*food.commands)(basic_food(food))


init_hooks()
