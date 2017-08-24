import codecs
import json
import os
import random
import time

from cloudbot import hook
from cloudbot.util.textgen import TextGenerator

hookups = {}
bites = {}
glomps = []


@hook.on_start
def load_data(bot):
    hookups.clear()
    glomps.clear()
    bites.clear()

    with codecs.open(os.path.join(bot.data_dir, "hookup.json"), encoding="utf-8") as f:
        hookups.update(json.load(f))

    with codecs.open(os.path.join(bot.data_dir, "glomp.txt"), encoding="utf-8") as f:
        lines = (line.strip() for line in f if not line.startswith("//"))
        glomps.extend(filter(None, lines))

    with codecs.open(os.path.join(bot.data_dir, "bite.json"), encoding="utf-8") as f:
        bites.update(json.load(f))


@hook.command(autohelp=False)
def hookup(db, chan):
    """matches two users from the channel in a sultry scene."""
    times = time.time() - 86400
    results = db.execute("select name from seen_user where chan = :chan and time > :time", {"chan": chan, "time": times}).fetchall()
    if not results or len(results) < 2:
        return "something went wrong"
    # Make sure the list of people is unique
    people = list(set(row[0] for row in results))
    random.shuffle(people)
    person1, person2 = people[:2]
    variables = {
        'user1': person1,
        'user2': person2,
    }
    generator = TextGenerator(hookups['templates'], hookups['parts'], variables=variables)
    return generator.generate_string()


@hook.command(autohelp=False)
def bite(text, chan, action):
    """bites the specified nick somewhere random."""
    if not text:
        return "please tell me who to bite."
    name = text.split(' ')[0]
    generator = TextGenerator(bites['templates'], bites['parts'], variables={'user': name})
    action(generator.generate_string(), chan)


@hook.command(autohelp=False)
def glomp(text, chan, action):
    """glomps the specified nick."""
    name = text.split(' ')[0]
    glomp = random.choice(glomps)
    out = "{} {}.".format(glomp, name)
    action(out, chan)
