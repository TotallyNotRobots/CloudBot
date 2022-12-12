# Chatgpt into gonzobot!
# Author: Matheus Fillipe
# Date: 31/07/2022

from functools import lru_cache
from time import time

from revChatGPT.revChatGPT import Chatbot

from cloudbot import hook
from cloudbot.bot import bot

RATELIMIT = False
MAX_PER_MINUTE = 2
MAX_PER_HOUR = 30


uses = {}


class Bot:
    def __init__(self, client):
        self.client = client

    def refresh(self):
        self.client.refresh_session()

    def query(self, message):
        return self.client.get_chat_response(message)['message']


@lru_cache(maxsize=1)
def _get_bot(**config):
    chatbot = Bot(Chatbot(config=config))
    return chatbot


def get_bot():
    api = bot.config.get_api_key("revchatgpt")
    user_agent = bot.config.get_api_key("user_agent")
    cf_clearance = bot.config.get_api_key("cf_clearance")

    config = {"session_token": api, 'Authorization': '',
              "cf_clearance": cf_clearance, "user_agent": user_agent}
    return _get_bot(**config)


@hook.command("gpt", "chat", autohelp=False)
async def chatgpt(text, message, chan, nick):
    """<message> - Chat with chatgpt"""
    global uses
    if RATELIMIT:
        if chan not in uses:
            uses[chan] = []

        last_hour_uses = sum([1 for i in uses[chan] if i > time() - 3600])
        last_minute_uses = sum([1 for i in uses[chan] if i > time() - 60])

        if last_hour_uses >= MAX_PER_HOUR:
            return "The command has reached the maximum uses per hour."
        if last_minute_uses >= MAX_PER_MINUTE:
            return "The command has reached the maximum uses per minute."

        uses[chan].append(time())

    bot = get_bot()
    try:
        response = bot.query(text)
    except Exception:
        bot.refresh()
        response = bot.query(text)

    output_lines = []
    for line in response.split("\n"):
        output_lines.extend([line[i:i + 500] for i in range(0, len(line), 500)])
    return output_lines


@hook.command("gptrefresh", "chatrefresh", autohelp=False)
async def chatgptrefresh(text, message, chan, nick):
    """<message> - Refresh chatgpt session"""
    bot = get_bot()
    bot.refresh()
    return "Chatgpt session refreshed!"
