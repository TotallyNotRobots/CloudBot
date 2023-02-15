import operator
import random
from collections import defaultdict
from threading import Lock
from time import sleep, time
from typing import Dict, List, NamedTuple, TypeVar

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    PrimaryKeyConstraint,
    String,
    Table,
    and_,
    desc,
)
from sqlalchemy.sql import select

from cloudbot import hook
from cloudbot.event import EventType
from cloudbot.util import database
from cloudbot.util.formatting import pluralize_auto, truncate
from cloudbot.util.func_utils import call_with_args

duck_tail = "・゜゜・。。・゜゜"
duck = [
    "\\_o< ",
    "\\_O< ",
    "\\_0< ",
    "\\_\u00f6< ",
    "\\_\u00f8< ",
    "\\_\u00f3< ",
]
duck_noise = ["QUACK!", "FLAP FLAP!", "quack!"]


class ScoreEntry(NamedTuple):
    network: str
    name: str
    chan: str
    shot: int = 0
    befriend: int = 0


table = Table(
    "duck_hunt",
    database.metadata,
    Column("network", String),
    Column("name", String),
    Column("shot", Integer),
    Column("befriend", Integer),
    Column("chan", String),
    PrimaryKeyConstraint("name", "chan", "network"),
)

optout = Table(
    "nohunt",
    database.metadata,
    Column("network", String),
    Column("chan", String),
    PrimaryKeyConstraint("chan", "network"),
)

status_table = Table(
    "duck_status",
    database.metadata,
    Column("network", String),
    Column("chan", String),
    Column("active", Boolean, default=False),
    Column("duck_kick", Boolean, default=False),
    PrimaryKeyConstraint("network", "chan"),
)


class ChannelState:
    """
    Represents the state of the hunt in a single channel
    """

    def __init__(self):
        self.masks = []
        self.messages = 0
        self.game_on = False
        self.no_duck_kick = False
        self.duck_status = 0
        self.next_duck_time = 0
        self.duck_time = 0
        self.shoot_time = 0

    def clear_messages(self):
        self.messages = 0
        self.masks.clear()

    def should_deploy(self, conn):
        """Should we deploy a duck?"""
        msg_delay = get_config(conn, "minimum_messages", 10)
        mask_req = get_config(conn, "minimum_users", 5)
        return (
            self.game_on
            and self.duck_status == 0
            and self.next_duck_time <= time()
            and self.messages >= msg_delay
            and len(self.masks) >= mask_req
        )

    def handle_message(self, event):
        if self.game_on and self.duck_status == 0:
            self.messages += 1
            if event.host not in self.masks:
                self.masks.append(event.host)


T = TypeVar("T")
ConnMap = Dict[str, Dict[str, T]]
scripters: Dict[str, float] = defaultdict(float)
chan_locks: ConnMap[Lock] = defaultdict(lambda: defaultdict(Lock))
game_status: ConnMap[ChannelState] = defaultdict(
    lambda: defaultdict(ChannelState)
)
opt_out: Dict[str, List[str]] = defaultdict(list)


def _get_conf_value(conf, field):
    return conf["plugins"]["duckhunt"][field]


def get_config(conn, field, default):
    try:
        return _get_conf_value(conn.config, field)
    except LookupError:
        try:
            return _get_conf_value(conn.bot.config, field)
        except LookupError:
            return default


@hook.on_start()
def load_optout(db):
    """load a list of channels duckhunt should be off in. Right now I am being lazy and not
    differentiating between networks this should be cleaned up later."""
    new_data = defaultdict(list)
    chans = db.execute(optout.select())
    for row in chans:
        chan = row["chan"]
        new_data[row["network"].casefold()].append(chan.casefold())

    opt_out.clear()
    opt_out.update(new_data)


def is_opt_out(network, chan):
    return chan.casefold() in opt_out[network]


@hook.on_start()
def load_status(db):
    rows = db.execute(status_table.select())
    for row in rows:
        net = row["network"]
        chan = row["chan"]
        status = get_state_table(net, chan)
        status.game_on = row["active"]
        status.no_duck_kick = row["duck_kick"]
        if status.game_on:
            set_ducktime(chan, net)


def get_state_table(network, chan):
    return game_status[network.casefold()][chan.casefold()]


def save_channel_state(db, network, chan, status=None):
    if status is None:
        status = get_state_table(network, chan)

    active = status.game_on
    duck_kick = status.no_duck_kick
    res = db.execute(
        status_table.update()
        .where(
            and_(status_table.c.network == network, status_table.c.chan == chan)
        )
        .values(active=active, duck_kick=duck_kick)
    )
    if not res.rowcount:
        db.execute(
            status_table.insert().values(
                network=network, chan=chan, active=active, duck_kick=duck_kick
            )
        )

    db.commit()


@hook.on_unload()
def save_on_exit(db):
    return save_status(db, False)


# @hook.periodic(8 * 3600, singlethread=True)  # Run every 8 hours
def save_status(db, _sleep=True):
    for network in game_status:
        for chan, status in game_status[network].items():
            save_channel_state(db, network, chan, status)

            if _sleep:
                sleep(5)


def set_game_state(db, conn, chan, active=None, duck_kick=None):
    status = get_state_table(conn.name, chan)
    if active is not None:
        status.game_on = active

    if duck_kick is not None:
        status.no_duck_kick = duck_kick

    save_channel_state(db, conn.name, chan, status)


@hook.event([EventType.message, EventType.action], singlethread=True)
def increment_msg_counter(event, conn):
    """Increment the number of messages said in an active game channel. Also keep track of the unique masks that are
    speaking.
    """
    if is_opt_out(conn.name, event.chan):
        return

    ignore = event.bot.plugin_manager.find_plugin("core.ignore")
    if ignore and ignore.code.is_ignored(conn.name, event.chan, event.mask):
        return

    get_state_table(conn.name, event.chan).handle_message(event)


@hook.command(
    "starthunt", autohelp=False, permissions=["chanop", "op", "botcontrol"]
)
def start_hunt(db, chan, message, conn):
    """- This command starts a duckhunt in your channel, to stop the hunt use .stophunt"""
    if is_opt_out(conn.name, chan):
        return None

    if not chan.startswith("#"):
        return "No hunting by yourself, that isn't safe."

    check = get_state_table(conn.name, chan).game_on
    if check:
        return "there is already a game running in {}.".format(chan)

    set_game_state(db, conn, chan, active=True)
    set_ducktime(chan, conn.name)
    message(
        "Ducks have been spotted nearby. "
        "See how many you can shoot or save. "
        "use .bang to shoot or .befriend to save them. "
        "NOTE: Ducks now appear as a function of time and channel activity.",
        chan,
    )
    return None


def set_ducktime(chan, conn):
    status = get_state_table(conn, chan)  # type: ChannelState
    status.next_duck_time = random.randint(
        int(time()) + 480, int(time()) + 3600
    )
    # status.flyaway = status.next_duck_time + 600
    status.duck_status = 0
    # let's also reset the number of messages said and the list of masks that have spoken.
    status.clear_messages()


@hook.command(
    "stophunt", autohelp=False, permissions=["chanop", "op", "botcontrol"]
)
def stop_hunt(db, chan, conn):
    """- This command stops the duck hunt in your channel. Scores will be preserved"""
    if is_opt_out(conn.name, chan):
        return None

    if get_state_table(conn.name, chan).game_on:
        set_game_state(db, conn, chan, active=False)
        return "the game has been stopped."

    return "There is no game running in {}.".format(chan)


@hook.command("duckkick", permissions=["chanop", "op", "botcontrol"])
def no_duck_kick(db, text, chan, conn, notice_doc):
    """<enable|disable> - If the bot has OP or half-op in the channel you can specify .duckkick enable|disable so that
    people are kicked for shooting or befriending a non-existent goose. Default is off.
    """
    if is_opt_out(conn.name, chan):
        return None

    if text.lower() == "enable":
        set_game_state(db, conn, chan, duck_kick=True)
        return (
            "users will now be kicked for shooting or befriending non-existent ducks. The bot needs to have "
            "appropriate flags to be able to kick users for this to work."
        )

    if text.lower() == "disable":
        set_game_state(db, conn, chan, duck_kick=False)
        return "kicking for non-existent ducks has been disabled."

    notice_doc()
    return None


def generate_duck():
    """Try and randomize the duck message so people can't highlight on it/script against it."""
    rt = random.randint(1, len(duck_tail) - 1)
    dtail = duck_tail[:rt] + " \u200b " + duck_tail[rt:]

    dbody = random.choice(duck)
    rb = random.randint(1, len(dbody) - 1)
    dbody = dbody[:rb] + "\u200b" + dbody[rb:]

    dnoise = random.choice(duck_noise)
    rn = random.randint(1, len(dnoise) - 1)
    dnoise = dnoise[:rn] + "\u200b" + dnoise[rn:]

    return dtail, dbody, dnoise


@hook.periodic(11, initial_interval=11)
def deploy_duck(bot):
    for network in game_status:
        if network not in bot.connections:
            continue

        conn = bot.connections[network]
        if not conn.ready:
            continue

        for chan in game_status[network]:
            status = get_state_table(network, chan)
            if not status.should_deploy(conn):
                continue

            # deploy a duck to channel
            status.duck_status = 1
            status.duck_time = time()
            dtail, dbody, dnoise = generate_duck()
            conn.message(chan, "{}{}{}".format(dtail, dbody, dnoise))


def hit_or_miss(deploy, shoot):
    """This function calculates if the befriend or bang will be successful."""
    if shoot - deploy < 1:
        return 0.05

    if 1 <= shoot - deploy <= 7:
        out = random.uniform(0.60, 0.75)
        return out

    return 1


def dbadd_entry(nick, chan, db, conn, shoot, friend):
    """Takes care of adding a new row to the database."""
    query = table.insert().values(
        network=conn.name,
        chan=chan.lower(),
        name=nick.lower(),
        shot=shoot,
        befriend=friend,
    )

    db.execute(query)
    db.commit()


def dbupdate(nick, chan, db, conn, shoot, friend):
    """update a db row"""
    values = {}
    if shoot:
        values["shot"] = shoot

    if friend:
        values["befriend"] = friend

    if not values:
        raise ValueError("No new values specified for 'friend' or 'shot'")

    query = (
        table.update()
        .where(
            and_(
                table.c.network == conn.name,
                table.c.chan == chan.lower(),
                table.c.name == nick.lower(),
            )
        )
        .values(**values)
    )

    db.execute(query)
    db.commit()


def update_score(nick, chan, db, conn, shoot=0, friend=0):
    score = db.execute(
        select([table.c.shot, table.c.befriend])
        .where(table.c.network == conn.name)
        .where(table.c.chan == chan.lower())
        .where(table.c.name == nick.lower())
    ).fetchone()

    if score:
        dbupdate(nick, chan, db, conn, score[0] + shoot, score[1] + friend)
        return {"shoot": score[0] + shoot, "friend": score[1] + friend}

    dbadd_entry(nick, chan, db, conn, shoot, friend)
    return {"shoot": shoot, "friend": friend}


def attack(event, nick, chan, db, conn, attack_type):
    if is_opt_out(conn.name, chan):
        return None

    network = conn.name
    status = get_state_table(network, chan)

    out = ""
    if attack_type == "shoot":
        miss = [
            "WHOOSH! You missed the duck completely!",
            "Your gun jammed!",
            "Better luck next time.",
            "WTF?! Who are you, Kim Jong Un firing missiles? You missed.",
        ]
        no_duck = "There is no duck! What are you shooting at?"
        msg = "{} you shot a duck in {:.3f} seconds! You have killed {} in {}."
        scripter_msg = (
            "You pulled the trigger in {:.3f} seconds, that's mighty fast. "
            "Are you sure you aren't a script? Take a 2 hour cool down."
        )
        attack_type = "shoot"
    else:
        miss = [
            "The duck didn't want to be friends, maybe next time.",
            "Well this is awkward, the duck needs to think about it.",
            "The duck said no, maybe bribe it with some pizza? Ducks love pizza don't they?",
            "Who knew ducks could be so picky?",
        ]
        no_duck = (
            "You tried befriending a non-existent duck. That's freaking creepy."
        )
        msg = "{} you befriended a duck in {:.3f} seconds! You have made friends with {} in {}."
        scripter_msg = (
            "You tried friending that duck in {:.3f} seconds, that's mighty fast. "
            "Are you sure you aren't a script? Take a 2 hour cool down."
        )
        attack_type = "friend"

    if not status.game_on:
        return "There is no hunt right now. Use .starthunt to start a game."

    if status.duck_status != 1:
        if status.no_duck_kick == 1:
            conn.cmd("KICK", chan, nick, no_duck)
            return None

        return no_duck

    status.shoot_time = time()
    deploy = status.duck_time
    shoot = status.shoot_time
    if nick.lower() in scripters:
        if scripters[nick.lower()] > shoot:
            event.notice(
                "You are in a cool down period, you can try again in {:.3f} seconds.".format(
                    scripters[nick.lower()] - shoot
                )
            )
            return None

    chance = hit_or_miss(deploy, shoot)
    if not random.random() <= chance and chance > 0.05:
        out = random.choice(miss) + " You can try again in 7 seconds."
        scripters[nick.lower()] = shoot + 7
        return out

    if chance == 0.05:
        out += scripter_msg.format(shoot - deploy)
        scripters[nick.lower()] = shoot + 7200
        return random.choice(miss) + " " + out

    status.duck_status = 2
    try:
        args = {attack_type: 1}

        score = update_score(nick, chan, db, conn, **args)[attack_type]
    except Exception:
        status.duck_status = 1
        event.reply("An unknown error has occurred.")
        raise

    event.message(
        msg.format(nick, shoot - deploy, pluralize_auto(score, "duck"), chan)
    )
    set_ducktime(chan, conn.name)
    return None


@hook.command("bang", autohelp=False)
def bang(nick, chan, db, conn, event):
    """- when there is a duck on the loose use this command to shoot it."""
    with chan_locks[conn.name][chan.casefold()]:
        return attack(event, nick, chan, db, conn, "shoot")


@hook.command("befriend", autohelp=False)
def befriend(nick, chan, db, conn, event):
    """- when there is a duck on the loose use this command to befriend it before someone else shoots it."""
    with chan_locks[conn.name][chan.casefold()]:
        return attack(event, nick, chan, db, conn, "befriend")


def top_list(prefix, data, join_char=" • "):
    r"""
    >>> foods = [('Spam', 1), ('Eggs', 4)]
    >>> top_list("Top Foods: ", foods)
    'Top Foods: \x02E\u200bggs\x02: 4 • \x02S\u200bpam\x02: 1'
    """
    sorted_data = sorted(data, key=operator.itemgetter(1), reverse=True)
    return truncate(
        prefix
        + join_char.join(
            "\x02{}\x02: {:,}".format(k[:1] + "\u200b" + k[1:], v)
            for k, v in sorted_data
        ),
        sep=join_char,
        length=320,
    )


def get_scores(db, score_type, network, chan=None):
    clause = table.c.network == network
    if chan is not None:
        clause = and_(clause, table.c.chan == chan.lower())

    query = select([table.c.name, table.c[score_type]], clause).order_by(
        desc(table.c[score_type])
    )

    scores = db.execute(query).fetchall()
    return scores


class ScoreType:
    def __init__(self, name, column_name, noun, verb):
        self.name = name
        self.column_name = column_name
        self.noun = noun
        self.verb = verb


def get_channel_scores(db, score_type: ScoreType, conn, chan):
    scores_dict: Dict[str, int] = defaultdict(int)
    scores = get_scores(db, score_type.column_name, conn.name, chan)
    if not scores:
        return None

    for row in scores:
        if row[1] == 0:
            continue

        scores_dict[row[0]] += row[1]

    return scores_dict


def _get_global_scores(db, score_type: ScoreType, conn):
    scores_dict: Dict[str, int] = defaultdict(int)
    chancount: Dict[str, int] = defaultdict(int)
    scores = get_scores(db, score_type.column_name, conn.name)
    if not scores:
        return None, None

    for row in scores:
        if row[1] == 0:
            continue

        chancount[row[0]] += 1
        scores_dict[row[0]] += row[1]

    return scores_dict, chancount


def get_global_scores(db, score_type: ScoreType, conn):
    return _get_global_scores(db, score_type, conn)[0]


def get_average_scores(db, score_type: ScoreType, conn):
    scores_dict, chancount = _get_global_scores(db, score_type, conn)
    if not scores_dict:
        return None

    for k, v in scores_dict.items():
        scores_dict[k] = int(v / chancount[k])

    return scores_dict


SCORE_TYPES = {
    "friend": ScoreType("befriend", "befriend", "friend", "friended"),
    "killer": ScoreType("killer", "shot", "killer", "killed"),
}

DISPLAY_FUNCS = {
    "average": get_average_scores,
    "global": get_global_scores,
    None: get_channel_scores,
}


def display_scores(score_type: ScoreType, event, text, chan, conn, db):
    if is_opt_out(conn.name, chan):
        return None

    global_pfx = "Duck {noun} scores across the network: ".format(
        noun=score_type.noun
    )
    chan_pfx = "Duck {noun} scores in {chan}: ".format(
        noun=score_type.noun, chan=chan
    )
    no_ducks = "It appears no one has {verb} any ducks yet.".format(
        verb=score_type.verb
    )

    out = global_pfx if text else chan_pfx

    try:
        func = DISPLAY_FUNCS[text.lower() or None]
    except KeyError:
        event.notice_doc()
        return None

    scores_dict = call_with_args(
        func,
        {
            "db": db,
            "score_type": score_type,
            "conn": conn,
            "chan": chan,
        },
    )

    if not scores_dict:
        return no_ducks

    return top_list(out, scores_dict.items())


@hook.command("friends", autohelp=False)
def friends(text, event, chan, conn, db):
    """[{global|average}] - Prints a list of the top duck friends in the
    channel, if 'global' is specified all channels in the database are
    included.
    """
    return display_scores(SCORE_TYPES["friend"], event, text, chan, conn, db)


@hook.command("killers", autohelp=False)
def killers(text, event, chan, conn, db):
    """[{global|average}] - Prints a list of the top duck killers in the
    channel, if 'global' is specified all channels in the database are
    included.
    """
    return display_scores(SCORE_TYPES["killer"], event, text, chan, conn, db)


@hook.command("duckforgive", permissions=["op", "ignore"])
def duckforgive(text):
    """<nick> - Allows people to be removed from the mandatory cooldown period."""
    if text.lower() in scripters and scripters[text.lower()] > time():
        scripters[text.lower()] = 0
        return "{} has been removed from the mandatory cooldown period.".format(
            text
        )

    return "I couldn't find anyone banned from the hunt by that nick"


@hook.command("hunt_opt_out", permissions=["op", "ignore"], autohelp=False)
def hunt_opt_out(text, chan, db, conn):
    """[{add <chan>|remove <chan>|list}] - Running this command without any arguments displays the status of the
    current channel. hunt_opt_out add #channel will disable all duck hunt commands in the specified channel.
    hunt_opt_out remove #channel will re-enable the game for the specified channel.
    """
    if not text:
        if is_opt_out(conn.name, chan):
            return "Duck hunt is disabled in {}. To re-enable it run .hunt_opt_out remove #channel".format(
                chan
            )

        return "Duck hunt is enabled in {}. To disable it run .hunt_opt_out add #channel".format(
            chan
        )

    if text == "list":
        return ", ".join(opt_out)

    if len(text.split(" ")) < 2:
        return "please specify add or remove and a valid channel name"

    command = text.split()[0]
    channel = text.split()[1]
    if not channel.startswith("#"):
        return "Please specify a valid channel."

    if command.lower() == "add":
        if is_opt_out(conn.name, channel):
            return "Duck hunt has already been disabled in {}.".format(channel)

        query = optout.insert().values(network=conn.name, chan=channel.lower())
        db.execute(query)
        db.commit()
        load_optout(db)
        return "The duckhunt has been successfully disabled in {}.".format(
            channel
        )

    if command.lower() == "remove":
        if not is_opt_out(conn.name, channel):
            return "Duck hunt is already enabled in {}.".format(channel)

        delete = optout.delete(optout.c.chan == channel.lower())
        db.execute(delete)
        db.commit()
        load_optout(db)

    return None


@hook.command("duckmerge", permissions=["botcontrol"])
def duck_merge(text, conn, db, message):
    """<user1> <user2> - Moves the duck scores from one nick to another nick. Accepts two nicks as input the first will
    have their duck scores removed the second will have the first score added. Warning this cannot be undone.
    """
    oldnick, newnick = text.lower().split()
    if not oldnick or not newnick:
        return "Please specify two nicks for this command."

    oldnickscore = db.execute(
        select([table.c.name, table.c.chan, table.c.shot, table.c.befriend])
        .where(table.c.network == conn.name)
        .where(table.c.name == oldnick)
    ).fetchall()

    newnickscore = db.execute(
        select([table.c.name, table.c.chan, table.c.shot, table.c.befriend])
        .where(table.c.network == conn.name)
        .where(table.c.name == newnick)
    ).fetchall()

    duckmerge: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total_kills = 0
    total_friends = 0
    channelkey: Dict[str, List[str]] = {"update": [], "insert": []}
    if not oldnickscore:
        return "There are no duck scores to migrate from {}".format(oldnick)

    new_chans = []

    for row in newnickscore:
        new_chans.append(row["chan"])
        chan_data = duckmerge[row["chan"]]
        chan_data["shot"] = row["shot"]
        chan_data["befriend"] = row["befriend"]

    for row in oldnickscore:
        chan_name = row["chan"]
        chan_data1 = duckmerge[chan_name]
        shot: int = row["shot"]
        _friends: int = row["befriend"]
        chan_data1["shot"] += shot
        chan_data1["befriend"] += _friends
        total_kills += shot
        total_friends += _friends
        if chan_name in new_chans:
            channelkey["update"].append(chan_name)
        else:
            channelkey["insert"].append(chan_name)

    for channel in channelkey["insert"]:
        dbadd_entry(
            newnick,
            channel,
            db,
            conn,
            duckmerge[channel]["shot"],
            duckmerge[channel]["befriend"],
        )

    for channel in channelkey["update"]:
        dbupdate(
            newnick,
            channel,
            db,
            conn,
            duckmerge[channel]["shot"],
            duckmerge[channel]["befriend"],
        )

    query = table.delete().where(
        and_(table.c.network == conn.name, table.c.name == oldnick)
    )

    db.execute(query)
    db.commit()
    message(
        "Migrated {} and {} from {} to {}".format(
            pluralize_auto(total_kills, "duck kill"),
            pluralize_auto(total_friends, "duck friend"),
            oldnick,
            newnick,
        )
    )
    return None


@hook.command("ducks", autohelp=False)
def ducks_user(text, nick, chan, conn, db, message):
    """<nick> - Prints a users duck stats. If no nick is input it will check the calling username."""
    name = nick.lower()
    if text:
        name = text.split()[0].lower()

    ducks: Dict[str, int] = defaultdict(int)
    scores = db.execute(
        select(
            [table.c.name, table.c.chan, table.c.shot, table.c.befriend],
            and_(
                table.c.network == conn.name,
                table.c.name == name,
            ),
        )
    ).fetchall()

    if text:
        name = text.split()[0]
    else:
        name = nick

    if scores:
        has_hunted_in_chan = False
        for row in scores:
            if row["chan"].lower() == chan.lower():
                has_hunted_in_chan = True
                ducks["chankilled"] += row["shot"]
                ducks["chanfriends"] += row["befriend"]

            ducks["killed"] += row["shot"]
            ducks["friend"] += row["befriend"]
            ducks["chans"] += 1

        # Check if the user has only participated in the hunt in this channel
        if ducks["chans"] == 1 and has_hunted_in_chan:
            message(
                "{} has killed {} and befriended {} in {}.".format(
                    name,
                    pluralize_auto(ducks["chankilled"], "duck"),
                    pluralize_auto(ducks["chanfriends"], "duck"),
                    chan,
                )
            )
            return None

        kill_average = int(ducks["killed"] / ducks["chans"])
        friend_average = int(ducks["friend"] / ducks["chans"])
        message(
            "\x02{}'s\x02 duck stats: \x02{}\x02 killed and \x02{}\x02 befriended in {}. "
            "Across {}: \x02{}\x02 killed and \x02{}\x02 befriended. "
            "Averaging \x02{}\x02 and \x02{}\x02 per channel.".format(
                name,
                pluralize_auto(ducks["chankilled"], "duck"),
                pluralize_auto(ducks["chanfriends"], "duck"),
                chan,
                pluralize_auto(ducks["chans"], "channel"),
                pluralize_auto(ducks["killed"], "duck"),
                pluralize_auto(ducks["friend"], "duck"),
                pluralize_auto(kill_average, "kill"),
                pluralize_auto(friend_average, "friend"),
            )
        )
        return None

    return "It appears {} has not participated in the duck hunt.".format(name)


@hook.command("duckstats", autohelp=False)
def duck_stats(chan, conn, db, message):
    """- Prints duck statistics for the entire channel and totals for the network."""
    scores = db.execute(
        select(
            [table.c.name, table.c.chan, table.c.shot, table.c.befriend],
            table.c.network == conn.name,
        )
    ).fetchall()
    friend_chan: Dict[str, int] = defaultdict(int)
    kill_chan: Dict[str, int] = defaultdict(int)
    chan_killed = 0
    chan_friends = 0
    killed = 0
    friends = 0
    chans = set()

    if scores:
        for row in scores:
            chan_name = row["chan"]
            chans.add(chan_name)
            friend_chan[chan_name] += row["befriend"]
            kill_chan[chan_name] += row["shot"]
            if chan_name.lower() == chan.lower():
                chan_killed += row["shot"]
                chan_friends += row["befriend"]

            killed += row["shot"]
            friends += row["befriend"]

        killerchan, killscore = sorted(
            kill_chan.items(), key=operator.itemgetter(1), reverse=True
        )[0]
        friendchan, friendscore = sorted(
            friend_chan.items(),
            key=operator.itemgetter(1),
            reverse=True,
        )[0]
        message(
            "\x02Duck Stats:\x02 {:,} killed and {:,} befriended in \x02{}\x02. "
            "Across {} \x02{:,}\x02 ducks have been killed and \x02{:,}\x02 befriended. "
            "\x02Top Channels:\x02 \x02{}\x02 with {} and \x02{}\x02 with {}".format(
                chan_killed,
                chan_friends,
                chan,
                pluralize_auto(len(chans), "channel"),
                killed,
                friends,
                killerchan,
                pluralize_auto(killscore, "kill"),
                friendchan,
                pluralize_auto(friendscore, "friend"),
            )
        )
        return None

    return "It looks like there has been no duck activity on this channel or network."
