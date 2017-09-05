import codecs
import json
import os
import asyncio
import re

from cloudbot import hook
from cloudbot.util import textgen

nick_re = re.compile("^[A-Za-z0-9_|.\-\]\[\{\}\*\`]*$", re.I)

sandwich_data = {}
taco_data = {}
coffee_data = {}
noodles_data = {}
muffin_data = {}
scone_data = {}
rice_data = {}
tea_data = {}
keto_data = {}
beer_data = {}
cheese_data = {}
pancake_data = {}
chicken_data = {}
icecream_data = {}
brekkie_data = {}
doobie_data = {}
pizza_data = {}
chocolate_data = {}
pasta_data = {}
nugget_data = {}
cereal_data = {}
pie_data = {}
sushi_data = {}
steak_data = {}
milkshake_data = {}
kebab_data = {}
cake_data = {}
potato_data = {}
cookie_data = {}


def is_valid(target):
    """ Checks if a string is a valid IRC nick. """
    if nick_re.match(target):
        return True
    else:
        return False


def load_template_data(bot, filename, data_dict):
    data_dict.clear()
    with codecs.open(os.path.join(bot.data_dir, filename), encoding="utf-8") as f:
        data_dict.update(json.load(f))


@hook.on_start()
def load_foods(bot):
    """
    :type bot: cloudbot.bot.CloudBot
    """

    load_template_data(bot, "sandwich.json", sandwich_data)
    load_template_data(bot, "taco.json", taco_data)
    load_template_data(bot, "coffee.json", coffee_data)
    load_template_data(bot, "noodles.json", noodles_data)
    load_template_data(bot, "muffin.json", muffin_data)
    load_template_data(bot, "scone.json", scone_data)
    load_template_data(bot, "rice.json", rice_data)
    load_template_data(bot, "tea.json", tea_data)
    load_template_data(bot, "keto.json", keto_data)
    load_template_data(bot, "beer.json", beer_data)
    load_template_data(bot, "cheese.json", cheese_data)
    load_template_data(bot, "pancake.json", pancake_data)
    load_template_data(bot, "chicken.json", chicken_data)
    load_template_data(bot, "nugget.json", nugget_data)
    load_template_data(bot, "pie.json", pie_data)
    load_template_data(bot, "brekkie.json", brekkie_data)
    load_template_data(bot, "icecream.json", icecream_data)
    load_template_data(bot, "doobie.json", doobie_data)
    load_template_data(bot, "pizza.json", pizza_data)
    load_template_data(bot, "chocolate.json", chocolate_data)
    load_template_data(bot, "pasta.json", pasta_data)
    load_template_data(bot, "cereal.json", cereal_data)
    load_template_data(bot, "sushi.json", sushi_data)
    load_template_data(bot, "steak.json", steak_data)
    load_template_data(bot, "milkshake.json", milkshake_data)
    load_template_data(bot, "kebab.json", kebab_data)
    load_template_data(bot, "cake.json", cake_data)
    load_template_data(bot, "potato.json", potato_data)
    load_template_data(bot, "cookies.json", cookie_data)


def basic_format(text, data, food_type, **kwargs):
    user = text
    kwargs['user'] = user

    if not is_valid(user):
        return "I can't give {} to that user.".format(food_type)

    generator = textgen.TextGenerator(
        data["templates"], data["parts"], variables=kwargs
    )

    return generator.generate_string()


@asyncio.coroutine
@hook.command
def potato(text, action):
    """<user> - makes <user> a tasty little potato"""
    # Kept for posterity
    # <Luke> Hey guys, any good ideas for plugins?
    # <User> I don't know, something that lists every potato known to man?
    # <Luke> BRILLIANT
    action(basic_format(text, potato_data, "a potato"))


@asyncio.coroutine
@hook.command
def cake(text, action):
    """<user> - gives <user> an awesome cake"""
    action(basic_format(text, cake_data, "a cake"))


@asyncio.coroutine
@hook.command
def cookie(text, action):
    """<user> - gives <user> a cookie"""
    action(basic_format(text, cookie_data, "a cookie"))


@asyncio.coroutine
@hook.command
def sandwich(text, action):
    """<user> - give a tasty sandwich to <user>"""
    action(basic_format(text, sandwich_data, "a sandwich"))

@asyncio.coroutine
@hook.command
def taco(text, action):
    """<user> - give a taco to <user>"""
    action(basic_format(text, taco_data, "a taco"))

@asyncio.coroutine
@hook.command
def coffee(text, action):
    """<user> - give coffee to <user>"""
    action(basic_format(text, coffee_data, "coffee"))


@asyncio.coroutine
@hook.command
def noodles(text, action):
    """<user> - give noodles to <user>"""
    action(basic_format(text, noodles_data, "noodles"))


@asyncio.coroutine
@hook.command
def muffin(text, action):
    """<user> - give muffin to <user>"""
    action(basic_format(text, muffin_data, "a muffin"))

@asyncio.coroutine
@hook.command
def scone(text, action):
    """<user> - give scone to <user>"""
    action(basic_format(text, scone_data, "a scone"))

@asyncio.coroutine
@hook.command
def rice(text, action):
    """<user> - give rice to <user>"""
    action(basic_format(text, rice_data, "rice"))

@asyncio.coroutine
@hook.command
def tea(text, action):
    """<user> - give tea to <user>"""
    action(basic_format(text, tea_data, "tea"))

@asyncio.coroutine
@hook.command
def keto(text, action):
    """<user> - give keto food to <user>"""
    action(basic_format(text, keto_data, "food"))

@asyncio.coroutine
@hook.command
def beer(text, action):
    """<user> - give beer to <user>"""
    action(basic_format(text, beer_data, "beer"))

@asyncio.coroutine
@hook.command
def cheese(text, action):
    """<user> - give cheese to <user>"""
    action(basic_format(text, cheese_data, "cheese"))

@asyncio.coroutine
@hook.command
def pancake(text, action):
    """<user> - give pancakes to <user>"""
    action(basic_format(text, pancake_data, "pancakes"))

@asyncio.coroutine
@hook.command
def chicken(text, action):
    """<user> - give chicken to <user>"""
    action(basic_format(text, chicken_data, "chicken"))

@asyncio.coroutine
@hook.command
def nugget(text, action):
    """<user> - give nuggets to <user>"""
    action(basic_format(text, nugget_data, "nuggets"))

@asyncio.coroutine
@hook.command
def pie(text, action):
    """<user> - give pie to <user>"""
    action(basic_format(text, pie_data, "pie"))

@asyncio.coroutine
@hook.command
def icecream(text, action):
    """<user> - give icecream to <user>"""
    action(basic_format(text, icecream_data, "icecream"))

@asyncio.coroutine
@hook.command("brekky", "brekkie")
def brekkie(text, action):
    """<user> - give brekkie to <user>"""
    action(basic_format(text, brekkie_data, "brekkie"))

@asyncio.coroutine
@hook.command("doobie")
def doobie(text, action):
    """<user> - pass the doobie to <user>"""
    action(basic_format(text, doobie_data, "a doobie"))

@asyncio.coroutine
@hook.command("pizza")
def pizza(text, action):
    """<user> - give pizza to <user>"""
    action(basic_format(text, pizza_data, "pizza"))

@asyncio.coroutine
@hook.command("chocolate")
def chocolate(text, action):
    """<user> - give chocolate to <user>"""
    action(basic_format(text, chocolate_data, "chocolate"))

@asyncio.coroutine
@hook.command
def pasta(text, action):
    """<user> - give pasta to <user>"""
    action(basic_format(text, pasta_data, "pasta"))

@asyncio.coroutine
@hook.command
def cereal(text, action):
    """<user> - give cereal to <user>"""
    action(basic_format(text, cereal_data, "cereal"))

@asyncio.coroutine
@hook.command
def sushi(text, action):
    """<user> - give sushi to <user>"""
    action(basic_format(text, sushi_data, "sushi"))

@asyncio.coroutine
@hook.command
def steak(text, action):
    """<user> - give a steak dinner to <user>"""
    action(basic_format(text, steak_data, "a nice steak dinner"))

@asyncio.coroutine
@hook.command
def milkshake(text, action):
    """<user> - give a milkshake to <user>"""
    action(basic_format(text, milkshake_data, "a milkshake"))

@asyncio.coroutine
@hook.command
def kebab(text, action):
    """<user> - give a kebab to <user>"""
    action(basic_format(text, kebab_data, "a delicious kebab"))
