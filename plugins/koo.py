from koo_api import KooAccount, KooAccountNotFoundException, KooPost

from cloudbot import hook
from cloudbot.util.queue import Queue

results_queue = Queue()


class BotKooPost(KooPost):
    def __str__(self):
        return f"{self.name} at {self.created_at.strftime('%d-%m-%Y %H:%M')} {self.likes_count}👍 - {self.content}"


@hook.command("koon", "koo_next", autohelp=False)
def koon(nick, chan, text):
    """Get next koo of your search results."""
    global results_queue
    results = results_queue[chan][nick]
    if results is None or len(results) == 0:
        return "No [more] results found."
    return str(results.pop())


@hook.command("koo", autohelp=False)
def koo(text, nick, chan, message):
    """<username> - Gets the koo of a user."""
    global results_queue
    if not text:
        return "Please enter a username."

    username = text.strip().split()[0]
    try:
        user = KooAccount(username)
    except KooAccountNotFoundException:
        return "User Account not found with that name."

    results_queue[chan][nick] = [
        BotKooPost.construct(**post.dict()) for post in user.get_posts(20)
    ]
    return koon(nick, chan, text)
