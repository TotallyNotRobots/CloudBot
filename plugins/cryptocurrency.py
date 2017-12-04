"""
cryptocurrency.py

A plugin that uses the CoinMarketCap JSON API to get values for cryptocurrencies.

Created By:
    - Luke Rogers <https://github.com/lukeroge>

License:
    GPL v3
"""
from datetime import datetime
from urllib.parse import quote_plus

import requests

from cloudbot import hook
from cloudbot.util import colors

API_URL = "https://api.coinmarketcap.com/v1/ticker/{}"

CURRENCY_SYMBOLS = {
    'USD': '$',
    'GBP': '£',
    'EUR': '€',
}


class Alias:
    __slots__ = ("name", "cmds")

    def __init__(self, name, *cmds):
        self.name = name
        if name not in cmds:
            cmds = (name,) + cmds

        self.cmds = cmds


ALIASES = (
    Alias('bitcoin', 'btc'),
    Alias('litecoin', 'ltc'),
    Alias('dogecoin', 'doge'),
)


def get_request(ticker, currency):
    return requests.get(API_URL.format(quote_plus(ticker)), params={'convert': currency})


def alias_wrapper(alias):
    def func(text):
        return crypto_command(" ".join((alias.name, text)))

    func.__doc__ = """- Returns the current {} value""".format(alias.name)
    func.__name__ = alias.name + "_alias"

    return func


def init_aliases():
    for alias in ALIASES:
        _hook = alias_wrapper(alias)
        globals()[_hook.__name__] = hook.command(*alias.cmds, autohelp=False)(_hook)


# main command
@hook.command("crypto", "cryptocurrency")
def crypto_command(text):
    """ <ticker> [currency] -- Returns current value of a cryptocurrency """
    args = text.split()
    ticker = args.pop(0)

    if not args:
        currency = 'USD'
    else:
        currency = args.pop(0).upper()

    try:
        request = get_request(ticker, currency)
        request.raise_for_status()
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
        return "Could not get value: {}".format(e)

    data = request.json()

    if "error" in data:
        return "{}.".format(data['error'])

    data = data[0]

    updated_time = datetime.fromtimestamp(float(data['last_updated']))
    if (datetime.today() - updated_time).days > 2:
        # the API retains data for old ticker names that are no longer updated
        # in these cases we just return a "not found" message
        return "Currency not found."

    change = float(data['percent_change_24h'])
    if change > 0:
        change_str = "$(dark_green) {}%$(clear)".format(change)
    elif change < 0:
        change_str = "$(dark_red) {}%$(clear)".format(change)
    else:
        change_str = "{}%".format(change)

    currency_sign = CURRENCY_SYMBOLS.get(currency, '')

    try:
        converted_value = data['price_' + currency.lower()]
    except LookupError:
        return "Unable to convert to currency '{}'".format(currency)

    return colors.parse("{} // $(orange){}{:,.2f}$(clear) {} - {:,.7f} BTC // {} change".format(
        data['symbol'], currency_sign, float(converted_value), currency.upper(),
        float(data['price_btc']), change_str
    ))
