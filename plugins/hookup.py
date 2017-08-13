import codecs
import json
import random
import time

import os

from cloudbot import hook
from cloudbot.util.textgen import TextGenerator

hookups = {}

bitesyns = ["bites", "nips", "nibbles", "chomps", "licks", "teases", "chews", "gums", "tastes"]
bodyparts = ["cheeks", "ear lobes", "nipples", "nose", "neck", "toes", "fingers", "butt", "taint", "thigh", "grundle", "tongue", "calf", "nurses", "nape"]

glomps = ["glomps", "tackles", "tackle hugs", "sexually glomps", "takes a flying leap and glomps", "bear hugs"]

usrcache = []


@hook.on_start
def load_hookups(bot):
    hookups.clear()
    with codecs.open(os.path.join(bot.data_dir, "hookup.json"), encoding="utf-8") as f:
        hookups.update(json.load(f))


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
    bite = random.choice(bitesyns)
    body = random.choice(bodyparts)
    out = "{} {}'s {}.".format(bite, name, body)
    action(out, chan)


@hook.command(autohelp=False)
def glomp(text, chan, action):
    """glomps the specified nick."""
    name = text.split(' ')[0]
    glomp = random.choice(glomps)
    out = "{} {}.".format(glomp, name)
    action(out, chan)
