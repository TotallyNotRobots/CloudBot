from re import findall
from typing import Dict

from cloudbot import hook
from cloudbot.util.formatting import get_text_list

polls: Dict[str, "Poll"] = {}


class PollError(Exception):
    pass


class PollOption:
    def __init__(self, title):
        self.title = title
        self.votes = 0


class Poll:
    def __init__(self, question, creator, options=("Yes", "No")):
        self.question = question
        self.creator = creator
        self.option_list = list(options)
        self.options = {i.lower(): PollOption(i) for i in options}

        self.voted = []

    def vote(self, voted_option, voter):
        """
        Adds a vote to a specific poll option. Raises PollError if option is invalid or user has already voted.
        Returns PollOption if sucessful.

        :param voted_option: The poll option to vote on
        :param voter: The user who is voting on the poll
        """
        voted_option = voted_option.lower()

        # check if the option is valid
        if voted_option not in self.options.keys():
            raise PollError("Sorry, that's not a valid option for this poll.")

        # make sure the user hasn't already voted
        if voter.lower() in self.voted:
            raise PollError("Sorry, you have already voted on this poll.")

        # fetch the option object, and increment option.votes
        option = self.options.get(voted_option)
        option.votes += 1

        self.voted.append(voter.lower())
        return option

    def format_results(self):
        # store a list of options, and sort by votes
        options = list(self.options.values())
        options.sort(key=lambda x: x.votes)

        output = []
        for o in self.options.values():
            string = "{}: {}".format(o.title, o.votes)
            output.append(string)

        return ", ".join(output)


@hook.command()
def poll(text, conn, nick, chan, message, reply):
    """{<question>[: <option1>, <option2>[, <option3>]...|close} - Creates a poll for [question] with the provided
    options (default: Yes, No), or closes the poll if the argument is 'close'"""
    # get poll ID
    uid = ":".join([conn.name, chan, nick]).lower()

    if text.lower() == "close":
        if uid not in polls.keys():
            return "You have no active poll to close."

        p = polls.get(uid)
        reply(
            'Your poll has been closed. Final results for \x02"{}"\x02:'.format(
                p.question
            )
        )
        message(p.format_results())
        del polls[uid]
        return None

    if uid in polls.keys():
        return "You already have an active poll in this channel, you must close it before you can create a new one."

    if ":" in text:
        question, options = text.strip().split(":")
        c = findall(r"([^,]+)", options)
        if len(c) == 1:
            c = findall(r"(\S+)", options)

        options = []
        for o in c:
            o = o.strip()
            if o not in options:
                options.append(o)

        _poll = Poll(question, nick, options)
    else:
        question = text.strip()
        _poll = Poll(question, nick)

    # store poll in list
    polls[uid] = _poll

    option_str = get_text_list(_poll.option_list, "and")
    message(
        'Created poll \x02"{}"\x02 with the following options: {}'.format(
            _poll.question, option_str
        )
    )
    message("Use .vote {} <option> to vote on this poll!".format(nick.lower()))
    return None


@hook.command(autohelp=True)
def vote(text, nick, conn, chan, notice):
    """<poll> <choice> - Vote on a poll; responds on error and silently records on success."""
    split = text.split(None, 1)
    if len(split) != 2:
        return (
            "Invalid input, please use .vote <user> <option> to vote on a poll."
        )

    _user, option = split
    uid = ":".join([conn.name, chan, _user]).lower()

    p = polls.get(uid)

    if p is None:
        return "Sorry, there is no active poll from that user."

    try:
        o = p.vote(option, nick)
    except PollError as e:
        return str(e)

    notice('Voted \x02"{}"\x02 on {}\'s poll!'.format(o.title, p.creator))
    return None


@hook.command(autohelp=False)
def results(text, conn, chan, nick, message, reply):
    """[user] - Shows current results from [user]'s poll. If [user] is empty, it will show results for your poll."""
    if text:
        uid = ":".join([conn.name, chan, text]).lower()
        if uid not in polls.keys():
            return "Sorry, there is no active poll from that user."
    else:
        uid = ":".join([conn.name, chan, nick]).lower()
        if uid not in polls.keys():
            return "You have no current poll. Use .vote <user> <option> to vote on another users poll."

    p = polls.get(uid)

    reply(
        'Results for \x02"{}"\x02 by \x02{}\x02:'.format(p.question, p.creator)
    )
    message(p.format_results())
    return None
