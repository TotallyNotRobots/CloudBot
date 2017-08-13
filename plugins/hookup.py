import random
import time

from cloudbot import hook

rooms = ["courtyard", "guest house", "observatory", "theatre", "drawing room", "garage", "spa", "master bedroom", "studio", "pool", "arcade", "beach house", "surf shop", "kitchen", "ballroom", "conservatory", "billiard room", "library", "study", "hallway", "lounge", "dining room", "cellar"]
weapons = ["a candlestick","an axe", "a pistol", "rope", "gloves", "a horseshoe", "a knife", "a baseball bat", "a chalice", "a dumbbell", "a wrench", "a trophy", "a pipe", "garden shears"]

bitesyns = ["bites", "nips", "nibbles", "chomps", "licks", "teases", "chews", "gums", "tastes"]
bodyparts = ["cheeks", "ear lobes", "nipples", "nose", "neck", "toes", "fingers", "butt", "taint", "thigh", "grundle", "tongue", "calf", "nurses", "nape"]

glomps = ["glomps", "tackles", "tackle hugs", "sexually glomps", "takes a flying leap and glomps", "bear hugs"]

usrcache = []

@hook.command(autohelp=False)
def hookup(db, conn, chan):
    """matches two users from the channel in a sultry scene."""
    times = time.time() - 86400
    results = db.execute("select name from seen_user where chan = :chan and time > :time", {"chan": chan, "time": times}).fetchall()
    if not results or len(results) < 2:
        return "something went wrong"
    # Make sure the list of people is unique
    people = list(set(row[0] for row in results))
    random.shuffle(people)
    person1, person2 = people[:2]
    room = random.choice(rooms)
    weapon = random.choice(weapons)
    out = "{} used {} and did it with {} in the {}.".format(person1, weapon, person2, room)
    return out

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
