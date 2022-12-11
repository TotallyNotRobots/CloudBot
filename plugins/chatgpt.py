# Chatgpt into gonzobot!
# Author: Matheus Fillipe
# Date: 31/07/2022

from functools import lru_cache

from revChatGPT.revChatGPT import Chatbot

from cloudbot import hook
from cloudbot.bot import bot
from time import time

RATELIMIT = True
MAX_PER_MINUTE = 3
MAX_PER_HOUR = 20


uses = {}


class Bot:
    def __init__(self, client):
        self.client = client

    def refresh(self):
        self.client.refresh_session()

    def query(self, message):
        return self.client.get_chat_response(message)['message']


@lru_cache(maxsize=1)
def get_bot():
    api = bot.config.get_api_key("revchatgpt")
    chatbot = Bot(Chatbot({"session_token": api, 'Authorization': ''}))
    return chatbot


@hook.on_start()
async def start_chatbot(async_call, db):
    get_bot()


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
    response = bot.query(text)
    response = ["".join(response[i:i + 500]) for i in range(0, len(response), 500)]
    lines = []
    for line in [n.split("\n") for n in response]:
        lines.extend(line)
    return lines


@hook.command("gptrefresh", "chatrefresh", autohelp=False)
async def chatgptrefresh(text, message, chan, nick):
    """<message> - Refresh chatgpt session"""
    bot = get_bot()
    bot.refresh()
    return "Chatgpt session refreshed!"
